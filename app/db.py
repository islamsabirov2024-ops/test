from __future__ import annotations
import json, os
from datetime import datetime, timedelta
import aiosqlite
from app.config import DB_PATH
SCHEMA=[
"""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,tg_user_id INTEGER UNIQUE,full_name TEXT DEFAULT '',username TEXT DEFAULT '',is_admin INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS user_bots(id INTEGER PRIMARY KEY AUTOINCREMENT,owner_user_id INTEGER NOT NULL,bot_token TEXT UNIQUE NOT NULL,bot_username TEXT DEFAULT '',bot_name TEXT DEFAULT '',bot_type_code TEXT NOT NULL,status TEXT DEFAULT 'pending_payment',tariff_code TEXT DEFAULT 'start',expires_at TEXT DEFAULT '',admin_id INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS bot_settings(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER UNIQUE,settings_json TEXT DEFAULT '{}',updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,user_bot_id INTEGER NOT NULL,amount INTEGER NOT NULL,days INTEGER DEFAULT 30,tariff_code TEXT DEFAULT 'start',status TEXT DEFAULT 'pending',receipt_file_id TEXT DEFAULT '',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TEXT DEFAULT '')""",
"""CREATE TABLE IF NOT EXISTS movies(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER NOT NULL,code TEXT NOT NULL,title TEXT DEFAULT '',chat_id TEXT NOT NULL,message_id INTEGER NOT NULL,caption TEXT DEFAULT '',is_premium INTEGER DEFAULT 0,views INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,UNIQUE(user_bot_id,code))""",
"""CREATE TABLE IF NOT EXISTS cleaner_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER,chat_id INTEGER,user_id INTEGER,reason TEXT,text TEXT DEFAULT '',created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
"""CREATE TABLE IF NOT EXISTS group_stats(id INTEGER PRIMARY KEY AUTOINCREMENT,user_bot_id INTEGER,chat_id INTEGER,user_id INTEGER,msg_count INTEGER DEFAULT 0,joined_count INTEGER DEFAULT 0,UNIQUE(user_bot_id,chat_id,user_id))"""
]
async def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        for q in SCHEMA: await db.execute(q)
        await db.commit()
async def add_user(tg_user_id:int, full_name:str, username:str='', is_admin:int=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO users(tg_user_id,full_name,username,is_admin) VALUES(?,?,?,?) ON CONFLICT(tg_user_id) DO UPDATE SET full_name=excluded.full_name,username=excluded.username,is_admin=MAX(users.is_admin,excluded.is_admin)",(tg_user_id,full_name,username,is_admin)); await db.commit()
async def create_user_bot(owner:int, token:str, username:str, name:str, typ:str)->int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("INSERT INTO user_bots(owner_user_id,bot_token,bot_username,bot_name,bot_type_code,admin_id) VALUES(?,?,?,?,?,?)",(owner,token,username,name,typ,owner)); bid=int(cur.lastrowid)
        await db.execute("INSERT OR IGNORE INTO bot_settings(user_bot_id,settings_json) VALUES(?,?)",(bid,'{}')); await db.commit(); return bid
async def row(q,*a):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row; cur=await db.execute(q,a); return await cur.fetchone()
async def rows(q,*a):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row; cur=await db.execute(q,a); return await cur.fetchall()
async def execq(q,*a):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(q,a); await db.commit()
async def list_user_bots(owner:int): return await rows('SELECT * FROM user_bots WHERE owner_user_id=? ORDER BY id DESC',owner)
async def list_active_bots(): return await rows("SELECT * FROM user_bots WHERE status='active'",)
async def get_bot(bid:int): return await row('SELECT * FROM user_bots WHERE id=?',bid)
async def set_bot_status(bid:int,status:str): await execq('UPDATE user_bots SET status=? WHERE id=?',status,bid)
async def delete_bot(bid:int,owner:int): await execq('DELETE FROM user_bots WHERE id=? AND owner_user_id=?',bid,owner)
async def set_bot_tariff(bid:int,tariff:str): await execq('UPDATE user_bots SET tariff_code=? WHERE id=?',tariff,bid)
async def add_bot_days(bid:int,days:int):
    b=await get_bot(bid); now=datetime.now(); base=now
    if b and b['expires_at']:
        try:
            old=datetime.strptime(b['expires_at'],'%Y-%m-%d %H:%M:%S')
            if old>now: base=old
        except Exception: pass
    new=(base+timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    await execq('UPDATE user_bots SET expires_at=? WHERE id=?',new,bid); return new
async def expire_due_bots(): return await rows("SELECT * FROM user_bots WHERE status='active' AND expires_at!='' AND expires_at < ?", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
async def get_settings(bid:int)->dict:
    r=await row('SELECT settings_json FROM bot_settings WHERE user_bot_id=?',bid)
    if not r: return {}
    try: return json.loads(r['settings_json'] or '{}')
    except Exception: return {}
async def save_settings(bid:int,data:dict): await execq('INSERT INTO bot_settings(user_bot_id,settings_json) VALUES(?,?) ON CONFLICT(user_bot_id) DO UPDATE SET settings_json=excluded.settings_json,updated_at=CURRENT_TIMESTAMP',bid,json.dumps(data,ensure_ascii=False))
async def create_payment(uid:int,bid:int,amount:int,days:int,tariff:str,file_id:str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("INSERT INTO payments(user_id,user_bot_id,amount,days,tariff_code,status,receipt_file_id) VALUES(?,?,?,?,?,'pending',?)",(uid,bid,amount,days,tariff,file_id)); await db.commit(); return int(cur.lastrowid)
async def get_payment(pid:int): return await row('SELECT p.*,b.bot_username,b.bot_name,b.bot_type_code,b.owner_user_id,b.bot_token FROM payments p JOIN user_bots b ON b.id=p.user_bot_id WHERE p.id=?',pid)
async def pending_payments(): return await rows("SELECT p.*,b.bot_username,b.bot_name,b.bot_type_code FROM payments p JOIN user_bots b ON b.id=p.user_bot_id WHERE p.status='pending' ORDER BY p.id DESC LIMIT 30")
async def set_payment_status(pid:int,status:str): await execq('UPDATE payments SET status=?,updated_at=? WHERE id=?',status,datetime.now().strftime('%Y-%m-%d %H:%M:%S'),pid)
async def add_movie(bid:int,code:str,title:str,chat_id:str,msg_id:int,caption:str=''):
    await execq('INSERT INTO movies(user_bot_id,code,title,chat_id,message_id,caption) VALUES(?,?,?,?,?,?) ON CONFLICT(user_bot_id,code) DO UPDATE SET title=excluded.title,chat_id=excluded.chat_id,message_id=excluded.message_id,caption=excluded.caption',bid,code.lower().strip(),title,chat_id,msg_id,caption)
async def get_movie(bid:int,code:str): return await row('SELECT * FROM movies WHERE user_bot_id=? AND code=?',bid,code.lower().strip())
async def list_movies(bid:int): return await rows('SELECT * FROM movies WHERE user_bot_id=? ORDER BY id DESC LIMIT 50',bid)
async def delete_movie(bid:int,code:str): await execq('DELETE FROM movies WHERE user_bot_id=? AND code=?',bid,code.lower().strip())
async def set_movie_premium(bid:int,code:str,val:int): await execq('UPDATE movies SET is_premium=? WHERE user_bot_id=? AND code=?',int(val),bid,code.lower().strip())
async def inc_movie_views(bid:int,code:str): await execq('UPDATE movies SET views=COALESCE(views,0)+1 WHERE user_bot_id=? AND code=?',bid,code.lower().strip())
async def add_clean_log(bid:int,chat_id:int,user_id:int,reason:str,text:str=''): await execq('INSERT INTO cleaner_logs(user_bot_id,chat_id,user_id,reason,text) VALUES(?,?,?,?,?)',bid,chat_id,user_id,reason,text[:300])
async def last_clean_logs(bid:int): return await rows('SELECT * FROM cleaner_logs WHERE user_bot_id=? ORDER BY id DESC LIMIT 10',bid)
async def inc_join(bid:int,chat_id:int,user_id:int): await execq('INSERT INTO group_stats(user_bot_id,chat_id,user_id,joined_count) VALUES(?,?,?,1) ON CONFLICT(user_bot_id,chat_id,user_id) DO UPDATE SET joined_count=joined_count+1',bid,chat_id,user_id)
