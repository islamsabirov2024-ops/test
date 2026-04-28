from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

import aiosqlite
from app.config import DB_PATH


# ================= CONNECT =================
async def connect():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ================= INIT =================
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_user_id INTEGER UNIQUE,
            full_name TEXT,
            username TEXT,
            is_admin INTEGER DEFAULT 0
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_user_id INTEGER,
            bot_token TEXT,
            bot_username TEXT,
            bot_name TEXT,
            bot_type_code TEXT,
            status TEXT DEFAULT 'pending_payment',
            expires_at TEXT DEFAULT ''
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_bot_id INTEGER,
            code TEXT,
            chat_id TEXT,
            message_id INTEGER,
            UNIQUE(user_bot_id, code)
        )
        """)

        await db.commit()


# ================= BASIC =================
async def execq(q: str, *a):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(q, a)
        await db.commit()


async def row(q: str, *a):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, a)
        return await cur.fetchone()


async def rows(q: str, *a):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(q, a)
        return await cur.fetchall()


# ================= USERS =================
async def add_user(uid: int, name: str, username: str = ""):
    await execq(
        "INSERT OR IGNORE INTO users(tg_user_id, full_name, username) VALUES(?,?,?)",
        uid, name, username
    )


# ================= BOT =================
async def create_user_bot(owner, token, username, name, typ):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO user_bots(owner_user_id, bot_token, bot_username, bot_name, bot_type_code)
            VALUES(?,?,?,?,?)
        """, (owner, token, username, name, typ))
        await db.commit()
        return cur.lastrowid


async def update_bot_token(bid, owner, token, username, name):
    await execq("""
        UPDATE user_bots
        SET bot_token=?, bot_username=?, bot_name=?
        WHERE id=? AND owner_user_id=?
    """, token, username, name, bid, owner)


async def get_bot(bid):
    return await row("SELECT * FROM user_bots WHERE id=?", bid)


async def list_user_bots(owner):
    return await rows("SELECT * FROM user_bots WHERE owner_user_id=?", owner)


async def set_bot_status(bid, status):
    await execq("UPDATE user_bots SET status=? WHERE id=?", status, bid)


# ================= MOVIES =================
async def add_movie(bid, code, chat_id, msg_id):
    await execq("""
        INSERT OR REPLACE INTO movies(user_bot_id, code, chat_id, message_id)
        VALUES(?,?,?,?)
    """, bid, code.lower(), chat_id, msg_id)


async def get_movie(bid, code):
    return await row("""
        SELECT * FROM movies WHERE user_bot_id=? AND code=?
    """, bid, code.lower())
