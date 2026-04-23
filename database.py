"""
database.py — хранение пользователей и найденных контактов
"""

import asyncpg
from datetime import datetime, date
from config import DB_URL, LEVEL_LIMITS, COOLDOWN_SECONDS

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host="aws-0-eu-west-1.pooler.supabase.com",
            port=5432,
            user="postgres.hwvonitemebjoxkclfin",
            password="shluhaebuchaya123.",
            database="postgres",
            ssl="require",
            min_size=2,
            max_size=10,
        )
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS parser_users (
                user_id      BIGINT PRIMARY KEY,
                username     TEXT DEFAULT '',
                level        INT DEFAULT 1,
                used_today   INT DEFAULT 0,
                last_reset   DATE DEFAULT CURRENT_DATE,
                cooldown_until TIMESTAMPTZ DEFAULT NULL,
                total_found  INT DEFAULT 0,
                joined_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS parser_contacts (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT,
                query       TEXT,
                country     TEXT,
                whatsapp    TEXT[],
                telegram    TEXT[],
                instagram   TEXT[],
                email       TEXT[],
                source_url  TEXT,
                source_name TEXT,
                found_at    TIMESTAMPTZ DEFAULT NOW()
            );
        """)


async def get_or_create_user(user_id: int, username: str = "") -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM parser_users WHERE user_id=$1", user_id)
        if row:
            user = dict(row)
            # Сбрасываем счётчик если новый день
            if user["last_reset"] < date.today():
                await conn.execute(
                    "UPDATE parser_users SET used_today=0, last_reset=CURRENT_DATE WHERE user_id=$1",
                    user_id,
                )
                user["used_today"] = 0
            return user
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        await conn.execute(
            "INSERT INTO parser_users (user_id, username, level, used_today, joined_at) VALUES ($1,$2,1,0,$3)",
            user_id, username, now,
        )
        return dict(await conn.fetchrow("SELECT * FROM parser_users WHERE user_id=$1", user_id))


async def get_user_limit(user_id: int) -> int:
    user = await get_or_create_user(user_id)
    level = user.get("level", 1)
    return LEVEL_LIMITS.get(level, 50)


async def get_remaining(user_id: int) -> int:
    user = await get_or_create_user(user_id)
    limit = LEVEL_LIMITS.get(user.get("level", 1), 50)
    return max(0, limit - user.get("used_today", 0))


async def is_on_cooldown(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT cooldown_until FROM parser_users WHERE user_id=$1", user_id
        )
        if row and row["cooldown_until"]:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            return row["cooldown_until"] > now
    return False


async def get_cooldown_left(user_id: int) -> int:
    """Возвращает секунды до конца кулдауна."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT cooldown_until FROM parser_users WHERE user_id=$1", user_id
        )
        if row and row["cooldown_until"]:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            delta = (row["cooldown_until"] - now).total_seconds()
            return max(0, int(delta))
    return 0


async def use_contacts(user_id: int, count: int):
    """Списывает использованные контакты."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM parser_users WHERE user_id=$1", user_id)
        if not user:
            return
        new_used = user["used_today"] + count
        limit = LEVEL_LIMITS.get(user["level"], 50)

        update_sql = "UPDATE parser_users SET used_today=$1, total_found=total_found+$2"
        params = [new_used, count]

        # Если лимит исчерпан — ставим кулдаун
        if new_used >= limit:
            from datetime import timedelta, timezone
            cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=COOLDOWN_SECONDS)
            update_sql += ", cooldown_until=$3 WHERE user_id=$4"
            params += [cooldown_until, user_id]
        else:
            update_sql += " WHERE user_id=$3"
            params.append(user_id)

        await conn.execute(update_sql, *params)


async def save_contacts(user_id: int, query: str, country: str, contacts_list: list):
    """Сохраняет найденные контакты в БД."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        for c in contacts_list:
            await conn.execute("""
                INSERT INTO parser_contacts
                (user_id, query, country, whatsapp, telegram, instagram, email, source_url, source_name)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """,
                user_id, query, country,
                list(c.get("whatsapp", set())),
                list(c.get("telegram", set())),
                list(c.get("instagram", set())),
                list(c.get("email", set())),
                c.get("source", ""),
                c.get("source_name", ""),
            )


async def set_user_level(user_id: int, level: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE parser_users SET level=$1 WHERE user_id=$2", level, user_id)


async def get_all_users() -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM parser_users ORDER BY total_found DESC")
        return [dict(r) for r in rows]
