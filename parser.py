"""
parser.py — парсинг объявлений и извлечение контактов
"""

import re
import asyncio
import logging
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# Паттерны контактов
RE_WHATSAPP  = re.compile(r"(?:wa\.me/|whatsapp\.com/send\?phone=|whatsapp[:\s]+)[\+]?([\d]{7,15})", re.I)
RE_TELEGRAM  = re.compile(r"(?:t\.me/|telegram\.me/|@)([a-zA-Z][a-zA-Z0-9_]{4,31})", re.I)
RE_INSTAGRAM = re.compile(r"instagram\.com/([a-zA-Z0-9_.]{3,30})/?", re.I)
RE_EMAIL     = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I)
RE_PHONE     = re.compile(r"[\+]?[\d][\d\s\-\(\)\.]{8,18}[\d]")
RE_WA_LINK   = re.compile(r"https?://(?:wa\.me|api\.whatsapp\.com/send)[^\s\"'<>]+", re.I)
RE_TG_LINK   = re.compile(r"https?://t\.me/[a-zA-Z][a-zA-Z0-9_]{4,31}", re.I)


def extract_contacts(text: str, url: str = "") -> dict:
    """Извлекает все контакты из текста."""
    contacts = {
        "whatsapp": set(),
        "telegram": set(),
        "instagram": set(),
        "email": set(),
        "phone": set(),
        "source": url,
    }

    # WhatsApp ссылки
    for m in RE_WA_LINK.finditer(text):
        link = m.group(0)
        num = RE_WHATSAPP.search(link)
        if num:
            contacts["whatsapp"].add(f"wa.me/{num.group(1)}")
        else:
            contacts["whatsapp"].add(link)

    # WhatsApp номера
    for m in RE_WHATSAPP.finditer(text):
        contacts["whatsapp"].add(f"wa.me/{m.group(1)}")

    # Telegram ссылки
    for m in RE_TG_LINK.finditer(text):
        link = m.group(0)
        username = link.split("t.me/")[-1].rstrip("/")
        if username and username.lower() not in ("joinchat", "share", "s"):
            contacts["telegram"].add(f"@{username}")

    # Telegram @username
    for m in RE_TELEGRAM.finditer(text):
        username = m.group(1)
        skip = {"gmail", "yahoo", "hotmail", "mail", "yandex", "icloud",
                "joinchat", "share", "channel", "group"}
        if username.lower() not in skip and len(username) >= 5:
            contacts["telegram"].add(f"@{username}")

    # Instagram
    for m in RE_INSTAGRAM.finditer(text):
        ig = m.group(1)
        skip = {"p", "reel", "stories", "explore", "accounts", "about"}
        if ig.lower() not in skip:
            contacts["instagram"].add(f"instagram.com/{ig}")

    # Email
    for m in RE_EMAIL.finditer(text):
        email = m.group(0)
        skip_domains = {"example.com", "test.com", "sentry.io", "w3.org"}
        domain = email.split("@")[-1].lower()
        if domain not in skip_domains:
            contacts["email"].add(email)

    return contacts


def has_contacts(c: dict) -> bool:
    return any(c.get(k) for k in ("whatsapp", "telegram", "instagram", "email"))


async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(
            url, headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=12),
            allow_redirects=True,
            ssl=False,
        ) as resp:
            if resp.status == 200:
                return await resp.text(errors="ignore")
    except Exception as e:
        logging.debug(f"fetch error {url}: {e}")
    return ""


async def parse_olx(session: aiohttp.ClientSession, url: str, query: str, country: str) -> list[dict]:
    """Парсит OLX."""
    results = []
    search_url = url.replace("{query}", quote(query)).replace("{cat}", "")
    html = await fetch_html(session, search_url)
    if not html:
        return results

    soup = BeautifulSoup(html, "lxml")
    # OLX использует разные классы в разных странах
    ads = (
        soup.select("div[data-cy='l-card']") or
        soup.select(".offer-wrapper") or
        soup.select("li.offer") or
        soup.select("div.css-1sw7q4x") or
        soup.select("article")
    )

    for ad in ads[:20]:
        text = ad.get_text(" ", strip=True)
        link_el = ad.find("a", href=True)
        link = link_el["href"] if link_el else ""
        if link and not link.startswith("http"):
            base = "/".join(url.split("/")[:3])
            link = base + link

        contacts = extract_contacts(text, link)
        if has_contacts(contacts):
            results.append(contacts)
        elif link:
            # Заходим на страницу объявления
            ad_html = await fetch_html(session, link)
            if ad_html:
                ad_contacts = extract_contacts(ad_html, link)
                if has_contacts(ad_contacts):
                    results.append(ad_contacts)
        await asyncio.sleep(0.3)

    return results


async def parse_jiji(session: aiohttp.ClientSession, url: str, query: str, country: str) -> list[dict]:
    """Парсит Jiji."""
    results = []
    search_url = url.replace("{query}", quote(query))
    html = await fetch_html(session, search_url)
    if not html:
        return results

    soup = BeautifulSoup(html, "lxml")
    ads = soup.select("article.b-list-advert__item") or soup.select("div.b-advert-card")

    for ad in ads[:20]:
        text = ad.get_text(" ", strip=True)
        link_el = ad.find("a", href=True)
        link = link_el["href"] if link_el else ""
        if link and not link.startswith("http"):
            base = "/".join(url.split("/")[:3])
            link = base + link

        contacts = extract_contacts(text, link)
        if has_contacts(contacts):
            results.append(contacts)
        elif link:
            ad_html = await fetch_html(session, link)
            if ad_html:
                ad_contacts = extract_contacts(ad_html, link)
                if has_contacts(ad_contacts):
                    results.append(ad_contacts)
        await asyncio.sleep(0.3)

    return results


async def parse_generic(session: aiohttp.ClientSession, url: str, query: str, country: str) -> list[dict]:
    """Универсальный парсер для любого сайта объявлений."""
    results = []
    search_url = url.replace("{query}", quote(query)).replace("{cat}", "")
    html = await fetch_html(session, search_url)
    if not html:
        return results

    soup = BeautifulSoup(html, "lxml")
    # Убираем скрипты
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    full_text = soup.get_text(" ", strip=True)
    contacts = extract_contacts(full_text, search_url)

    if has_contacts(contacts):
        results.append(contacts)

    # Ищем ссылки на объявления
    links = []
    for a in soup.find_all("a", href=True)[:30]:
        href = a["href"]
        if not href.startswith("http"):
            base = "/".join(search_url.split("/")[:3])
            href = base + href
        if any(kw in href for kw in ["/item", "/ad", "/offer", "/listing", "/post", "/annonce", "/imovel"]):
            links.append(href)

    for link in links[:10]:
        ad_html = await fetch_html(session, link)
        if ad_html:
            ad_contacts = extract_contacts(ad_html, link)
            if has_contacts(ad_contacts):
                results.append(ad_contacts)
        await asyncio.sleep(0.4)

    return results


async def parse_telegram(session: aiohttp.ClientSession, query: str, country: str) -> list[dict]:
    """Парсит публичные Telegram каналы через t.me/s/."""
    results = []
    # Ищем каналы через поиск
    search_queries = [
        f"{query} {country}",
        f"{query} wholesale {country}",
        f"{query} оптом",
    ]

    for q in search_queries[:2]:
        url = f"https://t.me/s/{quote(q.replace(' ', '_'))}"
        html = await fetch_html(session, url)
        if html:
            contacts = extract_contacts(html, url)
            if has_contacts(contacts):
                results.append(contacts)
        await asyncio.sleep(1)

    return results


PARSERS = {
    "olx":          parse_olx,
    "jiji":         parse_jiji,
    "generic":      parse_generic,
    "dubizzle":     parse_generic,
    "opensooq":     parse_generic,
    "mercadolibre": parse_generic,
    "craigslist":   parse_generic,
    "avito":        parse_generic,
}


async def search_all(query: str, country_code: str, limit: int = 50) -> list[dict]:
    """
    Главная функция поиска.
    Парсит все доступные источники для страны.
    """
    from sources import SOURCES

    sources = SOURCES.get(country_code, [])
    all_contacts = []
    seen = set()

    async with aiohttp.ClientSession() as session:
        # Telegram
        tg_results = await parse_telegram(session, query, country_code)
        for r in tg_results:
            key = str(sorted(r.get("whatsapp", set()) | r.get("telegram", set())))
            if key not in seen and key != "[]":
                seen.add(key)
                all_contacts.append(r)

        # Сайты объявлений
        for source in sources:
            if len(all_contacts) >= limit:
                break

            parser_fn = PARSERS.get(source["type"], parse_generic)
            try:
                results = await parser_fn(session, source["url"], query, country_code)
                for r in results:
                    key = str(sorted(r.get("whatsapp", set()) | r.get("telegram", set()) | r.get("email", set())))
                    if key not in seen and key != "[]":
                        seen.add(key)
                        r["source_name"] = source["name"]
                        all_contacts.append(r)
                        if len(all_contacts) >= limit:
                            break
            except Exception as e:
                logging.warning(f"Parser error {source['name']}: {e}")

            await asyncio.sleep(0.5)

    return all_contacts[:limit]
