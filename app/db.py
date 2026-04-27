from __future__ import annotations
import json, os
from datetime import datetime, timedelta
import aiosqlite
from app.config import DB_PATH

SCHEMA = [
"""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,tg_user_id INTEGER UNIQUE,full_name TEXT DEFAULT '',username TEXT DEFAULT '',is_admin INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS user_bots(id INTEGER PRIMARY KEY AUTOINCREMENT,owner_user_id INTEGER NOT NULL,bot_token TEXT NOT NULL UNIQUE,bot_username TEXT DEFAULT '',bot_name TEXT DEFAULT '',bot_type_code TEXT NOT NULL,status TEXT DEFAULT 'stopped',tariff_code TEXT DEFAULT 'standard',expires_at TEXT DEFAULT '',admin_id INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS bot_settings(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER UNIQUE,settings_json TEXT DEFAULT '{}',updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS movies(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER NOT NULL,code TEXT NOT NULL,title TEXT DEFAULT '',chat_id TEXT NOT NULL,message_id INTEGER NOT NULL,caption TEXT DEFAULT '',is_premium INTEGER DEFAULT 0,views INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_bot_id, code))""",
"""CREATE TABLE IF NOT EXISTS group_stats(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER NOT NULL,chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,msg_count INTEGER DEFAULT 0,joined_count INTEGER DEFAULT 0, UNIQUE(user_bot_id, chat_id, user_id))""",
]

async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        for q in SCHEMA:
            await db.execute(q)
        # eski app.db bo'lsa ustunlarni qo'shib yuboradi
        for col, typ in [('tariff_code', "TEXT DEFAULT 'standard'"), ('expires_at', "TEXT DEFAULT ''"), ('admin_id', 'INTEGER DEFAULT 0')]:
            try: await db.execute(f'ALTER TABLE user_bots ADD COLUMN {col} {typ}')
            except Exception: pass
        await db.commit()

async def add_user(tg_user_id:int, full_name:str, username:str='', is_admin:int=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO users(tg_user_id,full_name,username,is_admin) VALUES(?,?,?,?)
        ON CONFLICT(tg_user_id) DO UPDATE SET full_name=excluded.full_name,username=excluded.username""",(tg_user_id,full_name,username,is_admin))
        await db.commit()

async def create_user_bot(owner_user_id:int, token:str, username:str, name:str, bot_type:str) -> int:
    expires=(datetime.now()+timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("INSERT INTO user_bots(owner_user_id,bot_token,bot_username,bot_name,bot_type_code,status,tariff_code,expires_at,admin_id) VALUES(?,?,?,?,?,'stopped','standard',?,?)",(owner_user_id,token,username,name,bot_type,expires,owner_user_id))
        bot_id=cur.lastrowid
        await db.execute("INSERT OR IGNORE INTO bot_settings(user_bot_id,settings_json) VALUES(?,?)",(bot_id,'{}'))
        await db.commit(); return int(bot_id)

async def list_user_bots(owner_user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM user_bots WHERE owner_user_id=? ORDER BY id DESC",(owner_user_id,))
        return await cur.fetchall()
async def list_active_bots():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM user_bots WHERE status='active'")
        return await cur.fetchall()
async def get_bot(bot_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM user_bots WHERE id=?",(bot_id,)); return await cur.fetchone()
async def set_bot_status(bot_id:int,status:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_bots SET status=? WHERE id=?",(status,bot_id)); await db.commit()
async def delete_bot(bot_id:int, owner:int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM user_bots WHERE id=? AND owner_user_id=?",(bot_id,owner)); await db.commit()
async def set_bot_tariff(bot_id:int, tariff_code:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_bots SET tariff_code=? WHERE id=?",(tariff_code, bot_id)); await db.commit()
async def add_bot_days(bot_id:int, days:int):
    now=datetime.now()
    b=await get_bot(bot_id)
    base=now
    if b and b['expires_at']:
        try:
            old=datetime.strptime(b['expires_at'], '%Y-%m-%d %H:%M:%S')
            if old>now: base=old
        except Exception: pass
    new=(base+timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_bots SET expires_at=? WHERE id=?",(new, bot_id)); await db.commit()
    return new
async def count_user_bots(owner:int)->int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute('SELECT COUNT(*) FROM user_bots WHERE owner_user_id=?',(owner,)); row=await cur.fetchone(); return int(row[0] or 0)

async def get_settings(bot_id:int)->dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT settings_json FROM bot_settings WHERE user_bot_id=?",(bot_id,)); row=await cur.fetchone()
        if not row: return {}
        try: return json.loads(row['settings_json'] or '{}')
        except Exception: return {}
async def save_settings(bot_id:int, data:dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO bot_settings(user_bot_id,settings_json) VALUES(?,?) ON CONFLICT(user_bot_id) DO UPDATE SET settings_json=excluded.settings_json,updated_at=CURRENT_TIMESTAMP",(bot_id,json.dumps(data,ensure_ascii=False)))
        await db.commit()

async def add_movie(bot_id:int, code:str, title:str, chat_id:str, message_id:int, caption:str=''):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO movies(user_bot_id,code,title,chat_id,message_id,caption) VALUES(?,?,?,?,?,?)
        ON CONFLICT(user_bot_id,code) DO UPDATE SET title=excluded.title,chat_id=excluded.chat_id,message_id=excluded.message_id,caption=excluded.caption""",(bot_id,code.lower().strip(),title,chat_id,message_id,caption))
        await db.commit()
async def get_movie(bot_id:int, code:str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM movies WHERE user_bot_id=? AND code=?",(bot_id,code.lower().strip())); return await cur.fetchone()
async def list_movies(bot_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM movies WHERE user_bot_id=? ORDER BY id DESC LIMIT 30",(bot_id,)); return await cur.fetchall()
async def delete_movie(bot_id:int, code:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM movies WHERE user_bot_id=? AND code=?",(bot_id,code.lower().strip())); await db.commit()
async def inc_join(bot_id:int, chat_id:int, user_id:int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO group_stats(user_bot_id,chat_id,user_id,joined_count) VALUES(?,?,?,1) ON CONFLICT(user_bot_id,chat_id,user_id) DO UPDATE SET joined_count=joined_count+1",(bot_id,chat_id,user_id)); await db.commit()
