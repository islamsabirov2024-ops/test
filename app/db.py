import json, time
import aiosqlite
from .config import DATABASE_PATH

CREATE = [
"""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, ref_by INTEGER, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS bots(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, token TEXT UNIQUE, username TEXT, title TEXT, type TEXT DEFAULT 'kino', status TEXT DEFAULT 'active', created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS movies(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, code TEXT, file_id TEXT, source_chat_id TEXT, source_message_id INTEGER, caption TEXT, premium INTEGER DEFAULT 0, created_at INTEGER, UNIQUE(bot_id, code))""",
"""CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, title TEXT, chat_id TEXT, url TEXT, checkable INTEGER DEFAULT 1)""",
"""CREATE TABLE IF NOT EXISTS settings(bot_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(bot_id,key))""",
"""CREATE TABLE IF NOT EXISTS premium(bot_id INTEGER, user_id INTEGER, until_ts INTEGER, PRIMARY KEY(bot_id,user_id))""",
"""CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT, created_at INTEGER)"""
]

async def conn():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    async with await conn() as db:
        for q in CREATE: await db.execute(q)
        await db.commit()

async def add_user(user_id:int, ref_by=None):
    async with await conn() as db:
        await db.execute('INSERT OR IGNORE INTO users(user_id,ref_by,created_at) VALUES(?,?,?)',(user_id,ref_by,int(time.time())))
        await db.commit()

async def get_user(user_id:int):
    async with await conn() as db:
        cur=await db.execute('SELECT * FROM users WHERE user_id=?',(user_id,)); return await cur.fetchone()

async def add_bot(owner_id:int, token:str, username:str, title:str):
    async with await conn() as db:
        cur=await db.execute('INSERT INTO bots(owner_id,token,username,title,created_at) VALUES(?,?,?,?,?)',(owner_id,token,username,title,int(time.time())))
        await db.commit(); return cur.lastrowid

async def bots(owner_id=None):
    async with await conn() as db:
        if owner_id:
            cur=await db.execute('SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC',(owner_id,))
        else:
            cur=await db.execute('SELECT * FROM bots ORDER BY id DESC')
        return await cur.fetchall()

async def bot_by_id(bot_id:int):
    async with await conn() as db:
        cur=await db.execute('SELECT * FROM bots WHERE id=?',(bot_id,)); return await cur.fetchone()

async def set_bot_status(bot_id:int, status:str):
    async with await conn() as db:
        await db.execute('UPDATE bots SET status=? WHERE id=?',(status,bot_id)); await db.commit()

async def add_movie(bot_id:int, code:str, file_id=None, chat_id=None, msg_id=None, caption=''):
    async with await conn() as db:
        await db.execute('INSERT OR REPLACE INTO movies(bot_id,code,file_id,source_chat_id,source_message_id,caption,created_at) VALUES(?,?,?,?,?,?,?)',(bot_id,code.lower().strip(),file_id,chat_id,msg_id,caption,int(time.time())))
        await db.commit()

async def get_movie(bot_id:int, code:str):
    async with await conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip())); return await cur.fetchone()

async def list_movies(bot_id:int):
    async with await conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? ORDER BY id DESC LIMIT 50',(bot_id,)); return await cur.fetchall()

async def del_movie(bot_id:int, code:str):
    async with await conn() as db:
        await db.execute('DELETE FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip())); await db.commit()

async def add_channel(bot_id:int,title,chat_id,url,checkable=1):
    async with await conn() as db:
        await db.execute('INSERT INTO channels(bot_id,title,chat_id,url,checkable) VALUES(?,?,?,?,?)',(bot_id,title,chat_id,url,checkable)); await db.commit()

async def channels(bot_id:int):
    async with await conn() as db:
        cur=await db.execute('SELECT * FROM channels WHERE bot_id=?',(bot_id,)); return await cur.fetchall()

async def delete_channel(ch_id:int):
    async with await conn() as db:
        await db.execute('DELETE FROM channels WHERE id=?',(ch_id,)); await db.commit()

async def stat():
    async with await conn() as db:
        out={}
        for name,table in [('users','users'),('bots','bots'),('movies','movies'),('payments','payments')]:
            cur=await db.execute(f'SELECT COUNT(*) c FROM {table}'); out[name]=(await cur.fetchone())['c']
        return out
