"""
searcher.py — поиск через duckduckgo-search + парсинг контактов
"""

import re
import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}

# Паттерны для извлечения контактов
PATTERNS = {
    "email":     re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I),
    "telegram":  re.compile(r"(?:t\.me/|@)([a-zA-Z0-9_]{5,32})", re.I),
    "whatsapp":  re.compile(r"(?:wa\.me/|whatsapp[:\s]*[\+]?)([\d\s\-\(\)]{7,20})", re.I),
    "phone":     re.compile(r"(?<!\d)[\+]?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)"),
    "instagram": re.compile(r"instagram\.com/([a-zA-Z0-9_.]{3,30})/?", re.I),
    "vk":        re.compile(r"vk\.com/([a-zA-Z0-9_.]{3,50})/?", re.I),
}

# Шаблоны запросов для разных платформ
PLATFORM_QUERIES = {
    "instagram": [
        'site:instagram.com "{product}" "{geo}" WhatsApp',
        'site:instagram.com "{product}" "{geo}" Telegram',
        'site:instagram.com "{product}" "{geo}" оптом',
        'site:instagram.com "{product}" "{geo}" wholesale',
    ],
    "telegram": [
        'site:t.me "{product}" "{geo}"',
        'site:t.me/s/ "{product}" "{geo}" price',
        'telegram "{product}" "{geo}" оптом контакт',
    ],
    "facebook": [
        'site:facebook.com "{product}" "{geo}" WhatsApp',
        'site:facebook.com/groups/ "{product}" "{geo}" wholesale',
    ],
    "vk": [
        'site:vk.com "{product}" "{geo}" WhatsApp',
        'site:vk.com "{product}" "{geo}" оптом телефон',
    ],
    "any": [
        '"{product}" "{geo}" WhatsApp оптом поставщик',
        '"{product}" "{geo}" Telegram wholesale supplier',
        '"{product}" "{geo}" "@gmail.com" price list',
        '"{product}" "{geo}" intext:WhatsApp -job -vacancy',
        'поставщик "{product}" "{geo}" контакт телефон',
    ],
}


def build_queries(product: str, geo: str, platform: str) -> list[str]:
    templates = PLATFORM_QUERIES.get(platform, PLATFORM_QUERIES["any"])
    return [t.format(product=product, geo=geo) for t in templates]


def extract_contacts_from_text(text: str) -> dict:
    contacts = {k: set() for k in PATTERNS}
    for key, pattern in PATTERNS.items():
        found = pattern.findall(text)
        for item in found:
            val = item[0] if isinstance(item, tuple) else item
            val = val.strip()
            if val and len(val) > 2:
                contacts[key].add(val)
    return contacts


async def fetch_page_contacts(session: aiohttp.ClientSession, url: str) -> dict:
    contacts = {k: set() for k in PATTERNS}
    try:
        if not url.startswith("http"):
            url = "https://" + url
        async with session.get(
            url, headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=8),
            allow_redirects=True,
            ssl=False,
        ) as resp:
            if resp.status != 200:
                return contacts
            html = await resp.text(errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            # Убираем скрипты и стили
            for tag in soup(["script", "style", "meta"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
            page_contacts = extract_contacts_from_text(text)
            for k in page_contacts:
                contacts[k].update(page_contacts[k])
    except Exception as e:
        logging.debug(f"fetch_page error {url}: {e}")
    return contacts


def ddg_search_sync(query: str, max_results: int = 10) -> list[dict]:
    """Синхронный поиск через duckduckgo-search."""
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="off"):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as e:
        logging.warning(f"DDG search error: {e}")
    return results


async def search_contacts(product: str, geo: str, platform: str) -> list[dict]:
    queries = build_queries(product, geo, platform)
    all_results = []
    seen_urls = set()

    # Поиск (синхронный DDG в executor)
    loop = asyncio.get_event_loop()
    for query in queries[:4]:
        try:
            results = await loop.run_in_executor(
                None, lambda q=query: ddg_search_sync(q, max_results=8)
            )
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    # Контакты из сниппета
                    snippet_contacts = extract_contacts_from_text(
                        r.get("snippet", "") + " " + r.get("title", "")
                    )
                    r["contacts"] = snippet_contacts
                    all_results.append(r)
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.warning(f"Query error: {e}")
            continue

    if not all_results:
        return []

    # Парсим страницы для первых 6 результатов без контактов
    async with aiohttp.ClientSession() as session:
        tasks = []
        for r in all_results[:6]:
            has_contacts = any(r["contacts"].get(k) for k in r["contacts"])
            if not has_contacts and r.get("url"):
                tasks.append((r, r["url"]))

        for r, url in tasks:
            try:
                page_contacts = await asyncio.wait_for(
                    fetch_page_contacts(session, url), timeout=10
                )
                for k in page_contacts:
                    r["contacts"][k].update(page_contacts[k])
            except Exception:
                pass

    # Сортируем — сначала с контактами
    with_contacts = [r for r in all_results if any(r["contacts"].get(k) for k in r["contacts"])]
    without_contacts = [r for r in all_results if not any(r["contacts"].get(k) for k in r["contacts"])]

    return with_contacts + without_contacts


def format_results(results: list[dict], product: str, geo: str) -> str:
    if not results:
        return (
            "❌ <b>Контакты не найдены</b>\n\n"
            "Попробуйте:\n"
            "• Изменить товар (на английском)\n"
            "• Изменить гео (на английском)\n"
            "• Выбрать другую платформу\n"
            "• Попробовать «🌐 Везде»"
        )

    lines = [
        f"✅ <b>Результаты поиска</b>\n"
        f"📦 <b>{product}</b> | 🌍 <b>{geo}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
    ]

    shown = 0
    for r in results:
        contacts = r.get("contacts", {})
        contact_lines = []

        for email in list(contacts.get("email", set()))[:2]:
            if "@" in email and "." in email.split("@")[-1]:
                contact_lines.append(f"📧 <code>{email}</code>")

        for tg in list(contacts.get("telegram", set()))[:2]:
            if len(tg) >= 5:
                contact_lines.append(f"✈️ @{tg}")

        for wa in list(contacts.get("whatsapp", set()))[:1]:
            wa_clean = re.sub(r"[^\d+]", "", wa)
            if len(wa_clean) >= 7:
                contact_lines.append(f"📱 WhatsApp: <code>{wa_clean}</code>")

        for phone in list(contacts.get("phone", set()))[:1]:
            phone_clean = re.sub(r"\s", "", phone)
            contact_lines.append(f"📞 <code>{phone_clean}</code>")

        for ig in list(contacts.get("instagram", set()))[:1]:
            contact_lines.append(f"📸 instagram.com/{ig}")

        for vk in list(contacts.get("vk", set()))[:1]:
            contact_lines.append(f"🔵 vk.com/{vk}")

        title = r.get("title", "")[:55]
        url = r.get("url", "")[:70]

        if contact_lines:
            lines.append(
                f"<b>{shown + 1}. {title}</b>\n"
                f"🔗 {url}\n"
                + "\n".join(contact_lines)
                + "\n"
            )
            shown += 1
        elif shown < 3:
            lines.append(
                f"<b>{shown + 1}. {title}</b>\n"
                f"🔗 {url}\n"
                f"⚠️ Контакты не найдены\n"
            )
            shown += 1

        if shown >= 8:
            break

    lines.append(f"━━━━━━━━━━━━━━━━━\n📊 Показано: {shown} из {len(results)} результатов")
    return "\n".join(lines)
