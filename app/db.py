from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from app.config import DB_PATH


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_user_id INTEGER UNIQUE,
            full_name TEXT DEFAULT '',
            username TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER NOT NULL,
            bot_token TEXT UNIQUE NOT NULL,
            bot_username TEXT DEFAULT '',
            bot_name TEXT DEFAULT '',
            bot_type_code TEXT NOT NULL,
            status TEXT DEFAULT 'pending_payment',
            tariff_code TEXT DEFAULT 'start',
            expires_at TEXT DEFAULT '',
            admin_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER UNIQUE,
            settings_json TEXT DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_bot_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            days INTEGER DEFAULT 30,
            tariff_code TEXT DEFAULT 'start',
            status TEXT DEFAULT 'pending',
            receipt_file_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT ''
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            title TEXT DEFAULT '',
            chat_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            caption TEXT DEFAULT '',
            is_premium INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_bot_id, code)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS cleaner_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER,
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            text TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS group_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER,
            chat_id INTEGER,
            user_id INTEGER,
            msg_count INTEGER DEFAULT 0,
            joined_count INTEGER DEFAULT 0,
            UNIQUE(user_bot_id, chat_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS it_lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER NOT NULL,
            category TEXT DEFAULT 'python',
            title TEXT NOT NULL,
            body TEXT DEFAULT '',
            image_file_id TEXT DEFAULT '',
            price INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS lesson_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_bot_id, lesson_id, user_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS download_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER,
            user_id INTEGER,
            url TEXT,
            title TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Eski bazaga yangi columnlar qo‘shish
        migrations = [
            "ALTER TABLE user_bots ADD COLUMN bot_username TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN bot_name TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN bot_type_code TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN status TEXT DEFAULT 'pending_payment'",
            "ALTER TABLE user_bots ADD COLUMN tariff_code TEXT DEFAULT 'start'",
            "ALTER TABLE user_bots ADD COLUMN expires_at TEXT DEFAULT ''",
            "ALTER TABLE user_bots ADD COLUMN admin_id INTEGER DEFAULT 0",
            "ALTER TABLE user_bots ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE payments ADD COLUMN updated_at TEXT DEFAULT ''",
        ]

        for query in migrations:
            try:
                await db.execute(query)
            except Exception:
                pass

        await db.commit()


async def execq(query: str, *args: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, args)
        await db.commit()


async def row(query: str, *args: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, args)
        return await cur.fetchone()


async def rows(query: str, *args: Any):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(query, args)
        return await cur.fetchall()


async def add_user(tg_user_id: int, full_name: str, username: str = "", is_admin: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (tg_user_id, full_name, username, is_admin)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tg_user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username,
                is_admin = MAX(users.is_admin, excluded.is_admin)
            """,
            (tg_user_id, full_name, username, is_admin),
        )
        await db.commit()


async def create_user_bot(owner: int, token: str, username: str, name: str, typ: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO user_bots (
                owner_user_id,
                bot_token,
                bot_username,
                bot_name,
                bot_type_code,
                admin_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (owner, token, username, name, typ, owner),
        )
        bot_id = int(cur.lastrowid)

        await db.execute(
            """
            INSERT OR IGNORE INTO bot_settings (user_bot_id, settings_json)
            VALUES (?, ?)
            """,
            (bot_id, "{}"),
        )

        await db.commit()
        return bot_id


async def update_bot_token(bid: int, owner: int, token: str, username: str, name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            UPDATE user_bots
            SET bot_token = ?, bot_username = ?, bot_name = ?
            WHERE id = ? AND owner_user_id = ?
            """,
            (token, username, name, bid, owner),
        )
        await db.commit()
        return cur.rowcount > 0


async def list_user_bots(owner: int):
    return await rows(
        "SELECT * FROM user_bots WHERE owner_user_id = ? ORDER BY id DESC",
        owner,
    )


async def list_active_bots():
    return await rows(
        "SELECT * FROM user_bots WHERE status = 'active'"
    )


async def get_bot(bid: int):
    return await row(
        "SELECT * FROM user_bots WHERE id = ?",
        bid,
    )


async def get_user_bot_for_owner(bid: int, owner: int):
    return await row(
        "SELECT * FROM user_bots WHERE id = ? AND owner_user_id = ?",
        bid,
        owner,
    )


async def set_bot_status(bid: int, status: str):
    await execq(
        "UPDATE user_bots SET status = ? WHERE id = ?",
        status,
        bid,
    )


async def delete_bot(bid: int, owner: int):
    await execq(
        "DELETE FROM user_bots WHERE id = ? AND owner_user_id = ?",
        bid,
        owner,
    )


async def set_bot_tariff(bid: int, tariff: str):
    await execq(
        "UPDATE user_bots SET tariff_code = ? WHERE id = ?",
        tariff,
        bid,
    )


async def add_bot_days(bid: int, days: int) -> str:
    bot = await get_bot(bid)
    now = datetime.now()
    base = now

    if bot and bot["expires_at"]:
        try:
            old = datetime.strptime(bot["expires_at"], "%Y-%m-%d %H:%M:%S")
            if old > now:
                base = old
        except Exception:
            pass

    expires_at = (base + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    await execq(
        "UPDATE user_bots SET expires_at = ? WHERE id = ?",
        expires_at,
        bid,
    )

    return expires_at


async def expire_due_bots():
    return await rows(
        """
        SELECT *
        FROM user_bots
        WHERE status = 'active'
          AND expires_at != ''
          AND expires_at < ?
        """,
        _now(),
    )


async def get_settings(bid: int) -> dict:
    result = await row(
        "SELECT settings_json FROM bot_settings WHERE user_bot_id = ?",
        bid,
    )

    if not result:
        return {}

    try:
        return json.loads(result["settings_json"] or "{}")
    except Exception:
        return {}


async def save_settings(bid: int, data: dict):
    await execq(
        """
        INSERT INTO bot_settings (user_bot_id, settings_json)
        VALUES (?, ?)
        ON CONFLICT(user_bot_id) DO UPDATE SET
            settings_json = excluded.settings_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        bid,
        json.dumps(data, ensure_ascii=False),
    )


async def create_payment(uid: int, bid: int, amount: int, days: int, tariff: str, file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO payments (
                user_id,
                user_bot_id,
                amount,
                days,
                tariff_code,
                status,
                receipt_file_id
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (uid, bid, amount, days, tariff, file_id),
        )
        await db.commit()
        return int(cur.lastrowid)


async def get_payment(pid: int):
    return await row(
        """
        SELECT
            p.*,
            b.bot_username,
            b.bot_name,
            b.bot_type_code,
            b.owner_user_id,
            b.bot_token
        FROM payments p
        JOIN user_bots b ON b.id = p.user_bot_id
        WHERE p.id = ?
        """,
        pid,
    )


async def pending_payments():
    return await rows(
        """
        SELECT
            p.*,
            b.bot_username,
            b.bot_name,
            b.bot_type_code
        FROM payments p
        JOIN user_bots b ON b.id = p.user_bot_id
        WHERE p.status = 'pending'
        ORDER BY p.id DESC
        LIMIT 30
        """
    )


async def set_payment_status(pid: int, status: str):
    await execq(
        """
        UPDATE payments
        SET status = ?, updated_at = ?
        WHERE id = ?
        """,
        status,
        _now(),
        pid,
    )


async def add_movie(bid: int, code: str, title: str, chat_id: str, msg_id: int, caption: str = ""):
    await execq(
        """
        INSERT INTO movies (
            user_bot_id,
            code,
            title,
            chat_id,
            message_id,
            caption
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_bot_id, code) DO UPDATE SET
            title = excluded.title,
            chat_id = excluded.chat_id,
            message_id = excluded.message_id,
            caption = excluded.caption
        """,
        bid,
        code.lower().strip(),
        title,
        chat_id,
        msg_id,
        caption,
    )


async def get_movie(bid: int, code: str):
    return await row(
        "SELECT * FROM movies WHERE user_bot_id = ? AND code = ?",
        bid,
        code.lower().strip(),
    )


async def list_movies(bid: int):
    return await rows(
        "SELECT * FROM movies WHERE user_bot_id = ? ORDER BY id DESC LIMIT 50",
        bid,
    )


async def delete_movie(bid: int, code: str):
    await execq(
        "DELETE FROM movies WHERE user_bot_id = ? AND code = ?",
        bid,
        code.lower().strip(),
    )


async def set_movie_premium(bid: int, code: str, val: int):
    await execq(
        "UPDATE movies SET is_premium = ? WHERE user_bot_id = ? AND code = ?",
        int(val),
        bid,
        code.lower().strip(),
    )


async def inc_movie_views(bid: int, code: str):
    await execq(
        """
        UPDATE movies
        SET views = COALESCE(views, 0) + 1
        WHERE user_bot_id = ? AND code = ?
        """,
        bid,
        code.lower().strip(),
    )


async def add_clean_log(bid: int, chat_id: int, user_id: int, reason: str, text: str = ""):
    await execq(
        """
        INSERT INTO cleaner_logs (
            user_bot_id,
            chat_id,
            user_id,
            reason,
            text
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        bid,
        chat_id,
        user_id,
        reason,
        text[:300],
    )


async def last_clean_logs(bid: int):
    return await rows(
        "SELECT * FROM cleaner_logs WHERE user_bot_id = ? ORDER BY id DESC LIMIT 10",
        bid,
    )


async def inc_join(bid: int, chat_id: int, user_id: int):
    await execq(
        """
        INSERT INTO group_stats (
            user_bot_id,
            chat_id,
            user_id,
            joined_count
        )
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_bot_id, chat_id, user_id)
        DO UPDATE SET joined_count = joined_count + 1
        """,
        bid,
        chat_id,
        user_id,
    )


async def add_lesson(
    bid: int,
    category: str,
    title: str,
    body: str,
    image_file_id: str = "",
    price: int = 0,
):
    await execq(
        """
        INSERT INTO it_lessons (
            user_bot_id,
            category,
            title,
            body,
            image_file_id,
            price,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        bid,
        category,
        title,
        body,
        image_file_id,
        int(price),
    )


async def list_lessons(bid: int, category=None):
    if category:
        return await rows(
            """
            SELECT *
            FROM it_lessons
            WHERE user_bot_id = ?
              AND category = ?
              AND is_active = 1
            ORDER BY id ASC
            """,
            bid,
            category,
        )

    return await rows(
        """
        SELECT *
        FROM it_lessons
        WHERE user_bot_id = ?
          AND is_active = 1
        ORDER BY category ASC, id ASC
        """,
        bid,
    )


async def get_lesson(bid: int, lid: int):
    return await row(
        """
        SELECT *
        FROM it_lessons
        WHERE user_bot_id = ?
          AND id = ?
          AND is_active = 1
        """,
        bid,
        lid,
    )


async def delete_lesson(bid: int, lid: int):
    await execq(
        "UPDATE it_lessons SET is_active = 0 WHERE user_bot_id = ? AND id = ?",
        bid,
        lid,
    )


async def buy_lesson(bid: int, lid: int, uid: int):
    await execq(
        """
        INSERT OR IGNORE INTO lesson_purchases (
            user_bot_id,
            lesson_id,
            user_id
        )
        VALUES (?, ?, ?)
        """,
        bid,
        lid,
        uid,
    )


async def has_lesson(bid: int, lid: int, uid: int) -> bool:
    result = await row(
        """
        SELECT 1
        FROM lesson_purchases
        WHERE user_bot_id = ?
          AND lesson_id = ?
          AND user_id = ?
        """,
        bid,
        lid,
        uid,
    )
    return result is not None


async def seed_default_lessons(bid: int):
    existing = await rows(
        "SELECT id FROM it_lessons WHERE user_bot_id = ? LIMIT 1",
        bid,
    )

    if existing:
        return

    defaults = [
        (
            "python",
            "1-dars: Python nima?",
            'Python — bot, web va avtomatlashtirish uchun eng oson til.\n\nKod: print("Salom")',
            0,
        ),
        (
            "python",
            "2-dars: O‘zgaruvchilar",
            'name = "Islam"\nage = 18\nprint(name, age)',
            5000,
        ),
        (
            "bot",
            "1-dars: Telegram bot nima?",
            "BotFather orqali token olinadi. Keyin Python aiogram bilan ulaymiz.",
            0,
        ),
        (
            "bot",
            "2-dars: /start komandasi",
            "Router, Dispatcher va handler tushunchasi. Pullik dars namunasi.",
            10000,
        ),
        (
            "web",
            "1-dars: HTML boshlanishi",
            "HTML sahifa skeleti: <html><body>Salom</body></html>",
            0,
        ),
        (
            "db",
            "1-dars: Database nima?",
            "Ma’lumotlar bazasi user, kino, to‘lovlarni saqlaydi.",
            0,
        ),
        (
            "deploy",
            "1-dars: Render/Railway",
            "Deploy uchun requirements.txt, start command va env kerak.",
            0,
        ),
    ]

    for category, title, body, price in defaults:
        await add_lesson(bid, category, title, body, "", price)


async def add_download_log(bid: int, uid: int, url: str, title: str = ""):
    await execq(
        """
        INSERT INTO download_logs (
            user_bot_id,
            user_id,
            url,
            title
        )
        VALUES (?, ?, ?, ?)
        """,
        bid,
        uid,
        url,
        title[:200],
    )
