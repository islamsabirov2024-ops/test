import aiosqlite
import time
import os
from app.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  user_id INTEGER PRIMARY KEY,
  full_name TEXT,
  username TEXT,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS bots(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL,
  template TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  username TEXT,
  title TEXT,
  status TEXT NOT NULL DEFAULT 'pending_payment',
  price INTEGER DEFAULT 30000,
  card TEXT DEFAULT '',
  card_owner TEXT DEFAULT '',
  required_invites INTEGER DEFAULT 5,
  mute_seconds INTEGER DEFAULT 30,
  created_at INTEGER,
  paid_until INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bot_admins(
  bot_id INTEGER,
  user_id INTEGER,
  role TEXT DEFAULT 'admin',
  PRIMARY KEY(bot_id,user_id)
);
CREATE TABLE IF NOT EXISTS payments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER,
  user_id INTEGER,
  file_id TEXT,
  amount INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  created_at INTEGER,
  decided_at INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS movies(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER,
  code TEXT,
  title TEXT,
  file_id TEXT,
  source_chat_id TEXT,
  source_message_id INTEGER,
  is_premium INTEGER DEFAULT 0,
  views INTEGER DEFAULT 0,
  created_at INTEGER,
  UNIQUE(bot_id,code)
);
CREATE TABLE IF NOT EXISTS channels(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER,
  title TEXT,
  link TEXT,
  chat_id TEXT,
  is_checkable INTEGER DEFAULT 1,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS settings(
  bot_id INTEGER,
  key TEXT,
  value TEXT,
  PRIMARY KEY(bot_id,key)
);
CREATE TABLE IF NOT EXISTS subscribers(
  bot_id INTEGER,
  user_id INTEGER,
  username TEXT,
  full_name TEXT,
  created_at INTEGER,
  PRIMARY KEY(bot_id,user_id)
);
CREATE TABLE IF NOT EXISTS invite_counts(
  bot_id INTEGER,
  chat_id INTEGER,
  user_id INTEGER,
  count INTEGER DEFAULT 0,
  PRIMARY KEY(bot_id,chat_id,user_id)
);
"""

def connect():
    # Railway xatosi fix: connectionni async with dan oldin await qilmaymiz.
    if DATABASE_PATH and DATABASE_PATH not in {":memory:", ""}:
        folder = os.path.dirname(DATABASE_PATH)
        if folder:
            os.makedirs(folder, exist_ok=True)
    return aiosqlite.connect(DATABASE_PATH)

async def init_db():
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.executescript(SCHEMA)
        await db.commit()

async def upsert_user(user):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR REPLACE INTO users(user_id,full_name,username,created_at) VALUES(?,?,?,COALESCE((SELECT created_at FROM users WHERE user_id=?),?))",
                         (user.id, user.full_name, user.username or '', user.id, int(time.time())))
        await db.commit()

async def create_bot(owner_id:int, template:str, token:str, username:str='', title:str=''):
    now=int(time.time())
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("INSERT INTO bots(owner_id,template,token,username,title,status,created_at) VALUES(?,?,?,?,?,'pending_payment',?)",
                             (owner_id,template,token,username,title,now))
        bot_id=cur.lastrowid
        await db.execute("INSERT OR IGNORE INTO bot_admins(bot_id,user_id,role) VALUES(?,?,?)", (bot_id, owner_id, 'owner'))
        defaults={'premium_enabled':'0','force_sub_enabled':'0','ads_enabled':'0','welcome_text':'👋 Assalomu alaykum {name}!\n\n🎬 Kino kodini yuboring.','payment_text':'💳 To‘lov qilib chek rasmini yuboring.'}
        for k,v in defaults.items():
            await db.execute("INSERT OR REPLACE INTO settings(bot_id,key,value) VALUES(?,?,?)", (bot_id,k,v))
        await db.commit()
        return bot_id

async def list_bots(owner_id=None):
    q="SELECT * FROM bots ORDER BY id DESC"; args=[]
    if owner_id is not None:
        q="SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC"; args=[owner_id]
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute(q,args)
        return [dict(r) for r in await cur.fetchall()]

async def get_bot(bot_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM bots WHERE id=?",(bot_id,))
        r=await cur.fetchone(); return dict(r) if r else None

async def get_bot_by_token(token:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM bots WHERE token=?",(token,))
        r=await cur.fetchone(); return dict(r) if r else None

async def set_bot_status(bot_id:int,status:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE bots SET status=? WHERE id=?",(status,bot_id)); await db.commit()

async def update_bot_fields(bot_id:int, **fields):
    if not fields: return
    keys=list(fields.keys())
    sql="UPDATE bots SET "+", ".join(f"{k}=?" for k in keys)+" WHERE id=?"
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute(sql, [fields[k] for k in keys]+[bot_id]); await db.commit()

async def add_payment(bot_id:int,user_id:int,file_id:str,amount:int=0):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("INSERT INTO payments(bot_id,user_id,file_id,amount,created_at) VALUES(?,?,?,?,?)",(bot_id,user_id,file_id,amount,int(time.time())))
        await db.commit(); return cur.lastrowid

async def list_payments(status='pending'):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT p.*, b.username, b.template, b.owner_id FROM payments p LEFT JOIN bots b ON b.id=p.bot_id WHERE p.status=? ORDER BY p.id DESC",(status,))
        return [dict(r) for r in await cur.fetchall()]

async def decide_payment(payment_id:int,status:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE payments SET status=?, decided_at=? WHERE id=?",(status,int(time.time()),payment_id)); await db.commit()

async def set_setting(bot_id:int,key:str,value:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR REPLACE INTO settings(bot_id,key,value) VALUES(?,?,?)",(bot_id,key,str(value))); await db.commit()

async def get_setting(bot_id:int,key:str,default=''):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT value FROM settings WHERE bot_id=? AND key=?",(bot_id,key)); r=await cur.fetchone()
        return r['value'] if r else default

async def add_movie(bot_id:int,code:str,title:str='',file_id:str='',source_chat_id:str='',source_message_id:int=0,is_premium:int=0):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR REPLACE INTO movies(bot_id,code,title,file_id,source_chat_id,source_message_id,is_premium,created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (bot_id,code,title,file_id,source_chat_id,source_message_id,is_premium,int(time.time())))
        await db.commit()

async def get_movie(bot_id:int,code:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM movies WHERE bot_id=? AND code=?",(bot_id,code)); r=await cur.fetchone(); return dict(r) if r else None

async def list_movies(bot_id:int,limit:int=20):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM movies WHERE bot_id=? ORDER BY id DESC LIMIT ?",(bot_id,limit)); return [dict(r) for r in await cur.fetchall()]

async def delete_movie(bot_id:int,code:str):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM movies WHERE bot_id=? AND code=?",(bot_id,code)); await db.commit()

async def inc_movie_views(movie_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("UPDATE movies SET views=views+1 WHERE id=?",(movie_id,)); await db.commit()

async def add_channel(bot_id:int,title:str,link:str,chat_id:str,is_checkable:int=1):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT INTO channels(bot_id,title,link,chat_id,is_checkable,created_at) VALUES(?,?,?,?,?,?)",(bot_id,title,link,chat_id,is_checkable,int(time.time()))); await db.commit()

async def list_channels(bot_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM channels WHERE bot_id=? ORDER BY id DESC",(bot_id,)); return [dict(r) for r in await cur.fetchall()]

async def delete_channel(bot_id:int,channel_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("DELETE FROM channels WHERE bot_id=? AND id=?",(bot_id,channel_id)); await db.commit()

async def add_subscriber(bot_id:int,user):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR IGNORE INTO subscribers(bot_id,user_id,username,full_name,created_at) VALUES(?,?,?,?,?)",(bot_id,user.id,user.username or '',user.full_name,int(time.time()))); await db.commit()

async def stats(bot_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        data={}
        for name,table in [('movies','movies'),('channels','channels'),('users','subscribers')]:
            cur=await db.execute(f"SELECT COUNT(*) c FROM {table} WHERE bot_id=?",(bot_id,)); data[name]=(await cur.fetchone())['c']
        cur=await db.execute("SELECT COALESCE(SUM(views),0) c FROM movies WHERE bot_id=?",(bot_id,)); data['views']=(await cur.fetchone())['c']
        return data

async def is_bot_admin(bot_id:int,user_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT 1 FROM bot_admins WHERE bot_id=? AND user_id=?",(bot_id,user_id)); return await cur.fetchone() is not None

async def add_bot_admin(bot_id:int,user_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR IGNORE INTO bot_admins(bot_id,user_id,role) VALUES(?,?,?)",(bot_id,user_id,'admin')); await db.commit()

async def list_bot_admins(bot_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT * FROM bot_admins WHERE bot_id=?",(bot_id,)); return [dict(r) for r in await cur.fetchall()]

async def inc_invite(bot_id:int,chat_id:int,user_id:int,delta:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR IGNORE INTO invite_counts(bot_id,chat_id,user_id,count) VALUES(?,?,?,0)",(bot_id,chat_id,user_id))
        await db.execute("UPDATE invite_counts SET count=count+? WHERE bot_id=? AND chat_id=? AND user_id=?",(delta,bot_id,chat_id,user_id)); await db.commit()

async def get_invite_count(bot_id:int,chat_id:int,user_id:int):
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        cur=await db.execute("SELECT count FROM invite_counts WHERE bot_id=? AND chat_id=? AND user_id=?",(bot_id,chat_id,user_id)); r=await cur.fetchone(); return r['count'] if r else 0
