import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import BOT_TOKEN, ADMIN_IDS, LEVEL_LIMITS, COOLDOWN_SECONDS
import database as db
from sources import CATEGORIES, COUNTRIES
from parser import search_all

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ITEMS_PER_PAGE = 10


# ─── FSM ─────────────────────────────────────────────────────────────────────

class SearchFSM(StatesGroup):
    category = State()
    region   = State()
    country  = State()
    query    = State()
    running  = State()


# ─── Keyboards ────────────────────────────────────────────────────────────────

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти контакты")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )

def kb_cancel():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )

def kb_categories():
    cats = list(CATEGORIES.keys())
    rows = []
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=cats[i], callback_data=f"cat:{CATEGORIES[cats[i]]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=cats[i+1], callback_data=f"cat:{CATEGORIES[cats[i+1]]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_regions(page: int = 0):
    regions = list(COUNTRIES.keys())
    rows = []
    for region in regions:
        rows.append([InlineKeyboardButton(text=region, callback_data=f"region:{region}")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_countries(region: str, page: int = 0):
    countries = COUNTRIES.get(region, [])
    start = page * ITEMS_PER_PAGE
    chunk = countries[start:start + ITEMS_PER_PAGE]

    rows = []
    for i in range(0, len(chunk), 2):
        row = [InlineKeyboardButton(
            text=chunk[i][0],
            callback_data=f"country:{chunk[i][1]}:{chunk[i][0]}"
        )]
        if i + 1 < len(chunk):
            row.append(InlineKeyboardButton(
                text=chunk[i+1][0],
                callback_data=f"country:{chunk[i+1][1]}:{chunk[i+1][0]}"
            ))
        rows.append(row)

    # Навигация
    nav = []
    total_pages = (len(countries) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cpage:{region}:{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if (page + 1) * ITEMS_PER_PAGE < len(countries):
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"cpage:{region}:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="◀️ К регионам", callback_data="back_regions")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_contact(c: dict, idx: int, category: str, country_name: str) -> str:
    lines = [
        f"━━━━━━━━━━━━━━━━━",
        f"📦 Сфера: <b>{category}</b> ({country_name})",
        f"━━━━━━━━━━━━━━━━━",
    ]
    contact_num = 1
    for wa in list(c.get("whatsapp", set()))[:3]:
        lines.append(f"📱 Контакт {contact_num}: <a href='https://{wa}'>{wa}</a>")
        contact_num += 1
    for tg in list(c.get("telegram", set()))[:2]:
        lines.append(f"✈️ Контакт {contact_num}: {tg}")
        contact_num += 1
    for ig in list(c.get("instagram", set()))[:1]:
        lines.append(f"📸 Контакт {contact_num}: {ig}")
        contact_num += 1
    for email in list(c.get("email", set()))[:1]:
        lines.append(f"📧 Контакт {contact_num}: <code>{email}</code>")
        contact_num += 1
    src = c.get("source", "")
    src_name = c.get("source_name", "")
    if src:
        lines.append(f"🔗 Источник: {src_name or src[:50]}")
    return "\n".join(lines)


# ─── Handlers ────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username or "")
    level = user.get("level", 1)
    limit = LEVEL_LIMITS.get(level, 50)
    remaining = max(0, limit - user.get("used_today", 0))
    cooldown_min = COOLDOWN_SECONDS // 60

    await message.answer(
        f"🔍 <b>Парсер контактов</b>\n\n"
        f"🔑 Ваш уровень доступа: <b>{level}</b>\n"
        f"📊 Вам доступно <b>{remaining}</b> контактов сегодня.\n"
        f"⏱ Кулдаун: <b>{cooldown_min} минут</b> после исчерпания лимита\n\n"
        f"➡️ Выберите нужный пункт ниже:",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "👤 Профиль")
async def profile(message: Message):
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username or "")
    level = user.get("level", 1)
    limit = LEVEL_LIMITS.get(level, 50)
    used = user.get("used_today", 0)
    remaining = max(0, limit - used)
    total = user.get("total_found", 0)

    on_cd = await db.is_on_cooldown(message.from_user.id)
    cd_left = await db.get_cooldown_left(message.from_user.id) if on_cd else 0
    cd_str = f"⏳ Кулдаун: {cd_left // 60} мин {cd_left % 60} сек" if on_cd else "✅ Активен"

    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🔑 Уровень: <b>{level}</b>\n"
        f"📊 Лимит сегодня: <b>{used}/{limit}</b>\n"
        f"📈 Осталось: <b>{remaining}</b>\n"
        f"🏆 Всего найдено: <b>{total}</b>\n"
        f"🔄 Статус: {cd_str}",
        parse_mode="HTML",
    )


@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: Message):
    await message.answer(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Нажми <b>🔍 Найти контакты</b>\n"
        "2. Выбери категорию товара/услуги\n"
        "3. Выбери регион и страну\n"
        "4. Введи поисковый запрос\n\n"
        "📤 <b>Что получишь:</b>\n"
        "• WhatsApp номера (wa.me/...)\n"
        "• Telegram аккаунты\n"
        "• Instagram профили\n"
        "• Email адреса\n\n"
        "📌 <b>Источники:</b>\n"
        "• OLX (40+ стран)\n"
        "• Jiji (Африка)\n"
        "• Avito (Россия/СНГ)\n"
        "• Dubizzle (ОАЭ)\n"
        "• OpenSooq (Ближний Восток)\n"
        "• MercadoLibre (Латинская Америка)\n"
        "• Telegram каналы\n"
        "• И другие...\n\n"
        "⚠️ Поиск занимает 20-60 секунд.",
        parse_mode="HTML",
    )


@dp.message(F.text == "🔍 Найти контакты")
async def search_start(message: Message, state: FSMContext):
    await state.clear()

    # Проверка кулдауна
    if await db.is_on_cooldown(message.from_user.id):
        cd = await db.get_cooldown_left(message.from_user.id)
        await message.answer(
            f"⏳ <b>Лимит исчерпан.</b>\n\n"
            f"Следующий поиск доступен через: <b>{cd // 60} мин {cd % 60} сек</b>",
            parse_mode="HTML",
        ); return

    remaining = await db.get_remaining(message.from_user.id)
    if remaining <= 0:
        await message.answer("❌ Лимит контактов на сегодня исчерпан."); return

    await message.answer(
        f"📦 <b>Шаг 1/4 — Выберите категорию:</b>\n\n"
        f"📊 Осталось контактов: <b>{remaining}</b>",
        parse_mode="HTML",
        reply_markup=kb_categories(),
    )
    await state.set_state(SearchFSM.category)


@dp.callback_query(F.data == "cancel")
async def cancel_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer("Отменено.", reply_markup=main_menu())
    await call.answer()


@dp.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@dp.callback_query(SearchFSM.category, F.data.startswith("cat:"))
async def pick_category(call: CallbackQuery, state: FSMContext):
    cat_key = call.data.split(":", 1)[1]
    # Найти название категории
    from sources import CATEGORIES
    cat_name = next((k for k, v in CATEGORIES.items() if v == cat_key), cat_key)
    await state.update_data(category=cat_key, category_name=cat_name)

    await call.message.edit_text(
        f"🌍 <b>Шаг 2/4 — Выберите регион:</b>\n\n"
        f"📦 Категория: <b>{cat_name}</b>",
        parse_mode="HTML",
        reply_markup=kb_regions(),
    )
    await state.set_state(SearchFSM.region)
    await call.answer()


@dp.callback_query(SearchFSM.region, F.data.startswith("region:"))
async def pick_region(call: CallbackQuery, state: FSMContext):
    region = call.data.split(":", 1)[1]
    await state.update_data(region=region)
    data = await state.get_data()

    await call.message.edit_text(
        f"🌍 <b>Шаг 3/4 — Выберите страну:</b>\n\n"
        f"📦 Категория: <b>{data['category_name']}</b>\n"
        f"🌐 Регион: <b>{region}</b>",
        parse_mode="HTML",
        reply_markup=kb_countries(region, 0),
    )
    await state.set_state(SearchFSM.country)
    await call.answer()


@dp.callback_query(SearchFSM.country, F.data == "back_regions")
async def back_to_regions(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "🌍 <b>Выберите регион:</b>",
        parse_mode="HTML",
        reply_markup=kb_regions(),
    )
    await state.set_state(SearchFSM.region)
    await call.answer()


@dp.callback_query(SearchFSM.country, F.data.startswith("cpage:"))
async def country_page(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":")
    region = parts[1]
    page = int(parts[2])
    await call.message.edit_reply_markup(reply_markup=kb_countries(region, page))
    await call.answer()


@dp.callback_query(SearchFSM.country, F.data.startswith("country:"))
async def pick_country(call: CallbackQuery, state: FSMContext):
    parts = call.data.split(":", 2)
    country_code = parts[1]
    country_name = parts[2]
    await state.update_data(country_code=country_code, country_name=country_name)
    data = await state.get_data()

    await call.message.edit_text(
        f"🔍 <b>Шаг 4/4 — Введите запрос:</b>\n\n"
        f"📦 Категория: <b>{data['category_name']}</b>\n"
        f"🌍 Страна: <b>{country_name}</b>\n\n"
        f"<i>Например: leather bag, кожаная сумка, iPhone 15, квартира</i>",
        parse_mode="HTML",
    )
    await call.message.answer("✏️ Введите поисковый запрос:", reply_markup=kb_cancel())
    await state.set_state(SearchFSM.query)
    await call.answer()


@dp.message(SearchFSM.query, F.text == "❌ Отмена")
async def search_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu())


@dp.message(SearchFSM.query)
async def run_search(message: Message, state: FSMContext):
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос."); return

    data = await state.get_data()
    await state.set_state(SearchFSM.running)

    country_code = data["country_code"]
    country_name = data["country_name"]
    category_name = data["category_name"]
    remaining = await db.get_remaining(message.from_user.id)

    status_msg = await message.answer(
        f"⏳ <b>Ищу контакты...</b>\n\n"
        f"📦 {category_name} | 🌍 {country_name}\n"
        f"🔍 Запрос: <b>{query}</b>\n\n"
        f"Это займёт 20-60 секунд...",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )

    try:
        results = await search_all(query, country_code, limit=min(remaining, 50))
    except Exception as e:
        logging.error(f"Search error: {e}")
        results = []

    await state.clear()

    if not results:
        await status_msg.edit_text(
            f"❌ <b>Контакты не найдены</b>\n\n"
            f"📦 {category_name} | 🌍 {country_name}\n"
            f"🔍 Запрос: <b>{query}</b>\n\n"
            f"Попробуйте:\n"
            f"• Другой запрос (на английском)\n"
            f"• Другую страну\n"
            f"• Другую категорию",
            parse_mode="HTML",
        )
        return

    # Сохраняем и списываем
    await db.save_contacts(message.from_user.id, query, country_name, results)
    await db.use_contacts(message.from_user.id, len(results))

    await status_msg.edit_text(
        f"✅ <b>Найдено {len(results)} контактов!</b>\n\n"
        f"📦 {category_name} | 🌍 {country_name}",
        parse_mode="HTML",
    )

    # Отправляем контакты
    batch = []
    for i, c in enumerate(results):
        batch.append(format_contact(c, i + 1, category_name, country_name))

        if len(batch) >= 5 or i == len(results) - 1:
            text = "\n\n".join(batch)
            if len(text) > 4000:
                for item in batch:
                    try:
                        await message.answer(item, parse_mode="HTML", disable_web_page_preview=True)
                    except Exception:
                        pass
            else:
                try:
                    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
                except Exception:
                    pass
            batch = []
            await asyncio.sleep(0.3)

    # Итог
    remaining_after = await db.get_remaining(message.from_user.id)
    on_cd = await db.is_on_cooldown(message.from_user.id)
    if on_cd:
        cd = await db.get_cooldown_left(message.from_user.id)
        footer = f"⏳ Лимит исчерпан. Следующий поиск через {cd // 60} мин."
    else:
        footer = f"📊 Осталось контактов: <b>{remaining_after}</b>"

    await message.answer(
        f"✅ <b>Поиск завершён!</b>\n\n"
        f"📤 Отправлено: <b>{len(results)}</b> контактов\n"
        f"{footer}",
        parse_mode="HTML",
    )


# ─── Админ команды ────────────────────────────────────────────────────────────

@dp.message(Command("setlevel"))
async def admin_setlevel(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /setlevel user_id уровень"); return
    try:
        uid = int(args[1]); level = int(args[2])
        await db.set_user_level(uid, level)
        limit = LEVEL_LIMITS.get(level, 50)
        await message.answer(f"✅ Пользователю {uid} установлен уровень {level} ({limit} контактов/день)")
    except ValueError:
        await message.answer("❌ Неверные параметры")


@dp.message(Command("users"))
async def admin_users(message: Message):
    if not is_admin(message.from_user.id): return
    users = await db.get_all_users()
    if not users:
        await message.answer("Пользователей нет."); return
    lines = ["👥 <b>Пользователи:</b>\n"]
    for u in users[:20]:
        lines.append(
            f"• <code>{u['user_id']}</code> @{u['username']} | "
            f"Ур.{u['level']} | Сегодня: {u['used_today']} | Всего: {u['total_found']}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


# ─── Run ─────────────────────────────────────────────────────────────────────

async def main():
    await db.init_db()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
