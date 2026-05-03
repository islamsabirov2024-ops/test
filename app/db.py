import time
from contextlib import asynccontextmanager
import aiosqlite
from .config import DATABASE_PATH

CREATE = [
"""CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, ref_by INTEGER, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS global_settings(key TEXT PRIMARY KEY, value TEXT)""",
"""CREATE TABLE IF NOT EXISTS bots(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, token TEXT UNIQUE, username TEXT, title TEXT, type TEXT DEFAULT 'kino', status TEXT DEFAULT 'active', created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS movies(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, code TEXT, title TEXT DEFAULT '', caption TEXT DEFAULT '', premium INTEGER DEFAULT 0, created_at INTEGER, updated_at INTEGER, views INTEGER DEFAULT 0, UNIQUE(bot_id, code))""",
"""CREATE TABLE IF NOT EXISTS movie_parts(id INTEGER PRIMARY KEY AUTOINCREMENT, movie_id INTEGER, part_no INTEGER DEFAULT 1, name TEXT DEFAULT '', file_id TEXT, source_chat_id TEXT, source_message_id INTEGER, caption TEXT DEFAULT '', created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS movie_views(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, movie_id INTEGER, user_id INTEGER, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS favorites(bot_id INTEGER, user_id INTEGER, movie_id INTEGER, created_at INTEGER, PRIMARY KEY(bot_id,user_id,movie_id))""",
"""CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, title TEXT, chat_id TEXT, url TEXT, checkable INTEGER DEFAULT 1, pass_count INTEGER DEFAULT 0, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS settings(bot_id INTEGER, key TEXT, value TEXT, PRIMARY KEY(bot_id,key))""",
"""CREATE TABLE IF NOT EXISTS referral_wallets(bot_id INTEGER, user_id INTEGER, balance INTEGER DEFAULT 0, created_at INTEGER, PRIMARY KEY(bot_id,user_id))""",
"""CREATE TABLE IF NOT EXISTS premium(bot_id INTEGER, user_id INTEGER, until_ts INTEGER, reminded INTEGER DEFAULT 0, PRIMARY KEY(bot_id,user_id))""",
"""CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER DEFAULT 0, user_id INTEGER, tariff_id INTEGER DEFAULT 0, amount INTEGER, method TEXT, status TEXT, screenshot_file_id TEXT, created_at INTEGER, updated_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS tariffs(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, name TEXT, days INTEGER, price INTEGER, active INTEGER DEFAULT 1)""",
"""CREATE TABLE IF NOT EXISTS pay_methods(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, name TEXT, value TEXT, active INTEGER DEFAULT 1)""",
"""CREATE TABLE IF NOT EXISTS bot_admins(bot_id INTEGER, user_id INTEGER, PRIMARY KEY(bot_id,user_id))""",
"""CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, title TEXT, text TEXT, media_type TEXT DEFAULT '', file_id TEXT DEFAULT '', buttons TEXT DEFAULT '', start_enabled INTEGER DEFAULT 0, movie_enabled INTEGER DEFAULT 0, views INTEGER DEFAULT 0, active INTEGER DEFAULT 1, scheduled_at INTEGER DEFAULT 0, sent INTEGER DEFAULT 0, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, user_id INTEGER, text TEXT, status TEXT DEFAULT 'new', created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS admin_logs(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER, admin_id INTEGER, action TEXT, details TEXT, created_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS ad_deliveries(bot_id INTEGER, user_id INTEGER, ad_id INTEGER, delivered_at INTEGER)""",
"""CREATE TABLE IF NOT EXISTS runtime_events(id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id INTEGER DEFAULT 0, level TEXT, event TEXT, details TEXT, created_at INTEGER)""",
]

ALTERS = [
    "ALTER TABLE movies ADD COLUMN title TEXT DEFAULT ''",
    "ALTER TABLE movies ADD COLUMN updated_at INTEGER",
    "ALTER TABLE movies ADD COLUMN views INTEGER DEFAULT 0",
    "ALTER TABLE payments ADD COLUMN tariff_id INTEGER DEFAULT 0",
    "ALTER TABLE payments ADD COLUMN updated_at INTEGER",
    "ALTER TABLE channels ADD COLUMN pass_count INTEGER DEFAULT 0",
    "ALTER TABLE channels ADD COLUMN created_at INTEGER",
    "ALTER TABLE premium ADD COLUMN reminded INTEGER DEFAULT 0",
    "ALTER TABLE ads ADD COLUMN scheduled_at INTEGER DEFAULT 0",
    "ALTER TABLE ads ADD COLUMN sent INTEGER DEFAULT 0",
    "ALTER TABLE ads ADD COLUMN created_at INTEGER",
    "ALTER TABLE ads ADD COLUMN media_type TEXT DEFAULT ''",
    "ALTER TABLE ads ADD COLUMN file_id TEXT DEFAULT ''",
    "ALTER TABLE ads ADD COLUMN buttons TEXT DEFAULT ''",
    "ALTER TABLE referral_wallets ADD COLUMN created_at INTEGER",
]


INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_users_ref_by ON users(ref_by)",
    "CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_id)",
    "CREATE INDEX IF NOT EXISTS idx_bots_status ON bots(status)",
    "CREATE INDEX IF NOT EXISTS idx_movies_bot_code ON movies(bot_id, code)",
    "CREATE INDEX IF NOT EXISTS idx_movie_views_bot_user_time ON movie_views(bot_id, user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_movie_views_bot_time ON movie_views(bot_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_payments_bot_status ON payments(bot_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_premium_until ON premium(bot_id, until_ts)",
    "CREATE INDEX IF NOT EXISTS idx_ads_bot_active ON ads(bot_id, active)",
    "CREATE INDEX IF NOT EXISTS idx_ad_deliveries_user_time ON ad_deliveries(bot_id, user_id, delivered_at)",
]

@asynccontextmanager
async def conn():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    async with conn() as db:
        for q in CREATE:
            await db.execute(q)
        for q in ALTERS:
            try: await db.execute(q)
            except Exception: pass
        for q in INDEXES:
            try: await db.execute(q)
            except Exception: pass
        await db.commit()

async def add_user(user_id:int, ref_by=None):
    async with conn() as db:
        old = await (await db.execute('SELECT user_id FROM users WHERE user_id=?',(user_id,))).fetchone()
        await db.execute('INSERT OR IGNORE INTO users(user_id,ref_by,created_at) VALUES(?,?,?)',(user_id,ref_by,int(time.time())))
        if not old and ref_by and int(ref_by) != int(user_id):
            bonus_row = await (await db.execute('SELECT value FROM global_settings WHERE key=?',('referral_bonus',))).fetchone()
            bonus = int(bonus_row['value']) if bonus_row and str(bonus_row['value']).isdigit() else 0
            if bonus > 0:
                await db.execute('UPDATE users SET balance=COALESCE(balance,0)+? WHERE user_id=?',(bonus,int(ref_by)))
        await db.commit()
async def get_user(user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM users WHERE user_id=?',(user_id,)); return await cur.fetchone()
async def user_count(bot_id:int=None):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(*) c FROM users'); return (await cur.fetchone())['c']


async def add_balance(user_id:int, amount:int):
    async with conn() as db:
        await db.execute('INSERT OR IGNORE INTO users(user_id,balance,created_at) VALUES(?,?,?)',(user_id,0,int(time.time())))
        await db.execute('UPDATE users SET balance=COALESCE(balance,0)+? WHERE user_id=?',(int(amount),user_id))
        await db.commit()

async def take_balance(user_id:int, amount:int):
    amount=int(amount)
    if amount <= 0:
        return True
    async with conn() as db:
        await db.execute('BEGIN IMMEDIATE')
        await db.execute('INSERT OR IGNORE INTO users(user_id,balance,created_at) VALUES(?,?,?)',(user_id,0,int(time.time())))
        cur=await db.execute('UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?',(amount,user_id,amount))
        await db.commit()
        return cur.rowcount > 0

async def ref_count(user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(*) c FROM users WHERE ref_by=?',(user_id,)); return (await cur.fetchone())['c']

async def set_global(key:str, value):
    async with conn() as db:
        await db.execute('INSERT OR REPLACE INTO global_settings(key,value) VALUES(?,?)',(key,str(value))); await db.commit()

async def get_global(key:str, default=''):
    async with conn() as db:
        cur=await db.execute('SELECT value FROM global_settings WHERE key=?',(key,)); r=await cur.fetchone(); return r['value'] if r else default

async def add_bot(owner_id:int, token:str, username:str, title:str):
    async with conn() as db:
        cur=await db.execute('INSERT INTO bots(owner_id,token,username,title,created_at) VALUES(?,?,?,?,?)',(owner_id,token,username,title,int(time.time())))
        await db.commit(); return cur.lastrowid
async def bots(owner_id=None):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC',(owner_id,)) if owner_id else await db.execute('SELECT * FROM bots ORDER BY id DESC')
        return await cur.fetchall()
async def bot_by_id(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM bots WHERE id=?',(bot_id,)); return await cur.fetchone()
async def set_bot_status(bot_id:int, status:str):
    async with conn() as db:
        await db.execute('UPDATE bots SET status=? WHERE id=?',(status,bot_id)); await db.commit()

async def add_movie(bot_id:int, code:str, title:str='', caption:str='', premium:int=0):
    now=int(time.time()); code=code.lower().strip()
    async with conn() as db:
        old=await (await db.execute('SELECT id FROM movies WHERE bot_id=? AND code=?',(bot_id,code))).fetchone()
        if old:
            await db.execute('UPDATE movies SET title=?, caption=?, premium=?, updated_at=? WHERE id=?',(title,caption,int(premium),now,old['id']))
            await db.commit(); return old['id']
        cur=await db.execute('INSERT INTO movies(bot_id,code,title,caption,premium,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(bot_id,code,title,caption,int(premium),now,now))
        await db.commit(); return cur.lastrowid
async def get_movie(bot_id:int, code:str):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip())); return await cur.fetchone()
async def movie_by_id(movie_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE id=?',(movie_id,)); return await cur.fetchone()
async def list_movies(bot_id:int, limit:int=100):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? ORDER BY id DESC LIMIT ?',(bot_id,limit)); return await cur.fetchall()
async def latest_movies(bot_id:int, limit:int=20):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? ORDER BY created_at DESC LIMIT ?',(bot_id,limit)); return await cur.fetchall()
async def top_movies(bot_id:int, limit:int=20):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? ORDER BY views DESC, id DESC LIMIT ?',(bot_id,limit)); return await cur.fetchall()
async def search_movies(bot_id:int, q:str, limit:int=20):
    s=f"%{q.lower().strip()}%"
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movies WHERE bot_id=? AND (lower(title) LIKE ? OR lower(code) LIKE ?) ORDER BY id DESC LIMIT ?',(bot_id,s,s,limit)); return await cur.fetchall()

async def update_movie_field(bot_id:int, code:str, field:str, value):
    allowed={'title','caption'}
    if field not in allowed: return False
    async with conn() as db:
        await db.execute(f'UPDATE movies SET {field}=?, updated_at=? WHERE bot_id=? AND code=?',(value,int(time.time()),bot_id,code.lower().strip()))
        await db.commit()
        return True

async def update_movie_code(bot_id:int, old_code:str, new_code:str):
    old_code=old_code.lower().strip(); new_code=new_code.lower().strip()
    async with conn() as db:
        exists=await (await db.execute('SELECT id FROM movies WHERE bot_id=? AND code=?',(bot_id,new_code))).fetchone()
        if exists: return False
        cur=await db.execute('UPDATE movies SET code=?, updated_at=? WHERE bot_id=? AND code=?',(new_code,int(time.time()),bot_id,old_code))
        await db.commit()
        return cur.rowcount>0

async def del_movie(bot_id:int, code:str):
    async with conn() as db:
        r=await (await db.execute('SELECT id FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip()))).fetchone()
        if r: await db.execute('DELETE FROM movie_parts WHERE movie_id=?',(r['id'],))
        await db.execute('DELETE FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip())); await db.commit()
async def toggle_movie_premium(bot_id:int, code:str):
    async with conn() as db:
        cur=await db.execute('SELECT premium FROM movies WHERE bot_id=? AND code=?',(bot_id,code.lower().strip())); r=await cur.fetchone()
        if not r: return None
        new=0 if r['premium'] else 1
        await db.execute('UPDATE movies SET premium=?,updated_at=? WHERE bot_id=? AND code=?',(new,int(time.time()),bot_id,code.lower().strip())); await db.commit(); return new
async def add_part(movie_id:int, part_no:int, name:str, file_id=None, chat_id=None, msg_id=None, caption=''):
    async with conn() as db:
        await db.execute('INSERT INTO movie_parts(movie_id,part_no,name,file_id,source_chat_id,source_message_id,caption,created_at) VALUES(?,?,?,?,?,?,?,?)',(movie_id,part_no,name,file_id,chat_id,msg_id,caption,int(time.time())))
        await db.commit()
async def parts(movie_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movie_parts WHERE movie_id=? ORDER BY part_no ASC,id ASC',(movie_id,)); return await cur.fetchall()

async def next_part_no(movie_id:int):
    async with conn() as db:
        r=await (await db.execute('SELECT COALESCE(MAX(part_no),0)+1 n FROM movie_parts WHERE movie_id=?',(movie_id,))).fetchone()
        return int(r['n'] if r else 1)

async def part_by_id(part_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM movie_parts WHERE id=?',(part_id,)); return await cur.fetchone()

async def delete_movie(bot_id:int, code:str):
    return await del_movie(bot_id, code)

async def inc_view(bot_id:int, movie_id:int, user_id:int):
    async with conn() as db:
        await db.execute('UPDATE movies SET views=COALESCE(views,0)+1 WHERE id=?',(movie_id,))
        await db.execute('INSERT INTO movie_views(bot_id,movie_id,user_id,created_at) VALUES(?,?,?,?)',(bot_id,movie_id,user_id,int(time.time())))
        await db.commit()
async def toggle_fav(bot_id:int,user_id:int,movie_id:int):
    async with conn() as db:
        r=await (await db.execute('SELECT 1 FROM favorites WHERE bot_id=? AND user_id=? AND movie_id=?',(bot_id,user_id,movie_id))).fetchone()
        if r:
            await db.execute('DELETE FROM favorites WHERE bot_id=? AND user_id=? AND movie_id=?',(bot_id,user_id,movie_id)); await db.commit(); return False
        await db.execute('INSERT INTO favorites(bot_id,user_id,movie_id,created_at) VALUES(?,?,?,?)',(bot_id,user_id,movie_id,int(time.time()))); await db.commit(); return True
async def favorites(bot_id:int,user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT m.* FROM favorites f JOIN movies m ON m.id=f.movie_id WHERE f.bot_id=? AND f.user_id=? ORDER BY f.created_at DESC',(bot_id,user_id)); return await cur.fetchall()

async def add_channel(bot_id:int,title,chat_id,url,checkable=1):
    async with conn() as db:
        await db.execute('INSERT INTO channels(bot_id,title,chat_id,url,checkable,created_at) VALUES(?,?,?,?,?,?)',(bot_id,title,chat_id,url,checkable,int(time.time()))); await db.commit()
async def channels(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM channels WHERE bot_id=?',(bot_id,)); return await cur.fetchall()
async def delete_channel(ch_id:int):
    async with conn() as db:
        await db.execute('DELETE FROM channels WHERE id=?',(ch_id,)); await db.commit()
async def channel_pass(ch_id:int):
    async with conn() as db:
        await db.execute('UPDATE channels SET pass_count=COALESCE(pass_count,0)+1 WHERE id=?',(ch_id,)); await db.commit()

async def set_setting(bot_id:int,key,value):
    async with conn() as db:
        await db.execute('INSERT OR REPLACE INTO settings(bot_id,key,value) VALUES(?,?,?)',(bot_id,key,str(value))); await db.commit()
async def get_setting(bot_id:int,key,default=''):
    async with conn() as db:
        cur=await db.execute('SELECT value FROM settings WHERE bot_id=? AND key=?',(bot_id,key)); r=await cur.fetchone(); return r['value'] if r else default
async def add_tariff(bot_id:int,name:str,days:int,price:int):
    price=max(1000,min(1000000,int(price))); days=max(1,min(3650,int(days)))
    async with conn() as db:
        await db.execute('INSERT INTO tariffs(bot_id,name,days,price) VALUES(?,?,?,?)',(bot_id,name,days,price)); await db.commit()
async def tariffs(bot_id:int, active_only=False):
    async with conn() as db:
        q='SELECT * FROM tariffs WHERE bot_id=? '+('AND active=1 ' if active_only else '')+'ORDER BY price ASC'
        cur=await db.execute(q,(bot_id,)); return await cur.fetchall()
async def del_tariff(tid:int, bot_id:int):
    async with conn() as db:
        await db.execute('DELETE FROM tariffs WHERE id=? AND bot_id=?',(tid,bot_id)); await db.commit()
async def tariff_by_id(tid:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM tariffs WHERE id=?',(tid,)); return await cur.fetchone()
async def grant_premium(bot_id:int,user_id:int,days:int):
    now=int(time.time())
    async with conn() as db:
        r=await (await db.execute('SELECT until_ts FROM premium WHERE bot_id=? AND user_id=?',(bot_id,user_id))).fetchone()
        base=max(now, r['until_ts']) if r else now
        until=base+int(days)*86400
        await db.execute('INSERT OR REPLACE INTO premium(bot_id,user_id,until_ts,reminded) VALUES(?,?,?,0)',(bot_id,user_id,until)); await db.commit(); return until
async def remove_premium(bot_id:int,user_id:int):
    async with conn() as db:
        await db.execute('DELETE FROM premium WHERE bot_id=? AND user_id=?',(bot_id,user_id)); await db.commit()
async def has_premium(bot_id:int,user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT until_ts FROM premium WHERE bot_id=? AND user_id=?',(bot_id,user_id)); r=await cur.fetchone(); return bool(r and r['until_ts']>int(time.time()))
async def premium_list(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM premium WHERE bot_id=? AND until_ts>? ORDER BY until_ts DESC',(bot_id,int(time.time()))); return await cur.fetchall()
async def premium_due_reminders(bot_id:int):
    now=int(time.time()); day=now+86400
    async with conn() as db:
        cur=await db.execute('SELECT * FROM premium WHERE bot_id=? AND until_ts>? AND until_ts<=? AND reminded=0',(bot_id,now,day)); return await cur.fetchall()
async def mark_reminded(bot_id:int,user_id:int):
    async with conn() as db:
        await db.execute('UPDATE premium SET reminded=1 WHERE bot_id=? AND user_id=?',(bot_id,user_id)); await db.commit()

async def add_pay_method(bot_id:int,name:str,value:str):
    async with conn() as db:
        await db.execute('INSERT INTO pay_methods(bot_id,name,value) VALUES(?,?,?)',(bot_id,name,value)); await db.commit()
async def pay_methods(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM pay_methods WHERE bot_id=? AND active=1',(bot_id,)); return await cur.fetchall()
async def add_payment(bot_id:int,user_id:int,amount:int,method:str,status='pending',screenshot_file_id=None, tariff_id=0):
    async with conn() as db:
        cur=await db.execute('INSERT INTO payments(bot_id,user_id,tariff_id,amount,method,status,screenshot_file_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(bot_id,user_id,tariff_id,amount,method,status,screenshot_file_id,int(time.time()),int(time.time())))
        await db.commit(); return cur.lastrowid
async def payment_by_id(pid:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM payments WHERE id=?',(pid,)); return await cur.fetchone()
async def payments(bot_id:int=None,status=None,user_id=None):
    async with conn() as db:
        cond=[]; vals=[]
        if bot_id is not None: cond.append('bot_id=?'); vals.append(bot_id)
        if status: cond.append('status=?'); vals.append(status)
        if user_id is not None: cond.append('user_id=?'); vals.append(user_id)
        q='SELECT * FROM payments '+(('WHERE '+' AND '.join(cond)) if cond else '')+' ORDER BY id DESC LIMIT 100'
        cur=await db.execute(q,vals); return await cur.fetchall()
async def update_payment(pid:int,status:str):
    async with conn() as db:
        await db.execute('UPDATE payments SET status=?,updated_at=? WHERE id=?',(status,int(time.time()),pid)); await db.commit()

async def add_admin(bot_id:int,user_id:int):
    async with conn() as db:
        await db.execute('INSERT OR IGNORE INTO bot_admins(bot_id,user_id) VALUES(?,?)',(bot_id,user_id)); await db.commit()
async def del_admin(bot_id:int,user_id:int):
    async with conn() as db:
        await db.execute('DELETE FROM bot_admins WHERE bot_id=? AND user_id=?',(bot_id,user_id)); await db.commit()
async def admins(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM bot_admins WHERE bot_id=?',(bot_id,)); return await cur.fetchall()
async def is_bot_admin(bot_id:int,user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT 1 FROM bot_admins WHERE bot_id=? AND user_id=?',(bot_id,user_id)); return bool(await cur.fetchone())

async def add_ad(bot_id:int,title,text,scheduled_at=0,media_type='',file_id='',buttons=''):
    async with conn() as db:
        await db.execute('INSERT INTO ads(bot_id,title,text,media_type,file_id,buttons,scheduled_at,created_at) VALUES(?,?,?,?,?,?,?,?)',(bot_id,title,text,media_type or '',file_id or '',buttons or '',int(scheduled_at or 0),int(time.time()))); await db.commit()
async def ads(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM ads WHERE bot_id=? ORDER BY id DESC',(bot_id,)); return await cur.fetchall()
async def active_ad(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM ads WHERE bot_id=? AND active=1 ORDER BY id DESC LIMIT 1',(bot_id,)); return await cur.fetchone()
async def inc_ad_view(ad_id:int):
    async with conn() as db:
        await db.execute('UPDATE ads SET views=COALESCE(views,0)+1 WHERE id=?',(ad_id,)); await db.commit()
async def scheduled_ads(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM ads WHERE bot_id=? AND scheduled_at>0 AND scheduled_at<=? AND sent=0 AND active=1',(bot_id,int(time.time()))); return await cur.fetchall()
async def mark_ad_sent(ad_id:int):
    async with conn() as db:
        await db.execute('UPDATE ads SET sent=1 WHERE id=?',(ad_id,)); await db.commit()
async def toggle_ad(bot_id:int, field:str):
    key='ad_'+field; curv=await get_setting(bot_id,key,'0'); new='0' if curv=='1' else '1'; await set_setting(bot_id,key,new); return new

async def add_request(bot_id:int,user_id:int,text:str):
    async with conn() as db:
        await db.execute('INSERT INTO requests(bot_id,user_id,text,created_at) VALUES(?,?,?,?)',(bot_id,user_id,text,int(time.time()))); await db.commit()
async def requests(bot_id:int,status=None):
    async with conn() as db:
        if status: cur=await db.execute('SELECT * FROM requests WHERE bot_id=? AND status=? ORDER BY id DESC LIMIT 100',(bot_id,status))
        else: cur=await db.execute('SELECT * FROM requests WHERE bot_id=? ORDER BY id DESC LIMIT 100',(bot_id,))
        return await cur.fetchall()
async def set_request_status(req_id:int,status:str):
    async with conn() as db:
        await db.execute('UPDATE requests SET status=? WHERE id=?',(status,req_id)); await db.commit()

async def add_log(bot_id:int,admin_id:int,action:str,details:str=''):
    async with conn() as db:
        await db.execute('INSERT INTO admin_logs(bot_id,admin_id,action,details,created_at) VALUES(?,?,?,?,?)',(bot_id,admin_id,action,details,int(time.time()))); await db.commit()
async def logs(bot_id:int,limit:int=50):
    async with conn() as db:
        cur=await db.execute('SELECT * FROM admin_logs WHERE bot_id=? ORDER BY id DESC LIMIT ?',(bot_id,limit)); return await cur.fetchall()
async def delete_pay_method(bot_id:int, pay_id:int):
    async with conn() as db:
        await db.execute('DELETE FROM pay_methods WHERE id=? AND bot_id=?',(pay_id,bot_id)); await db.commit()

async def update_tariff(tid:int, bot_id:int, field:str, value):
    allowed={'name','days','price'}
    if field not in allowed: return False
    if field=='price': value=max(1000,min(1000000,int(value)))
    if field=='days': value=max(1,min(3650,int(value)))
    async with conn() as db:
        await db.execute(f'UPDATE tariffs SET {field}=? WHERE id=? AND bot_id=?',(value,tid,bot_id)); await db.commit(); return True

async def referral_balance(bot_id:int,user_id:int):
    async with conn() as db:
        r=await (await db.execute('SELECT balance FROM referral_wallets WHERE bot_id=? AND user_id=?',(bot_id,user_id))).fetchone()
        return int(r['balance']) if r else 0

async def add_referral_balance(bot_id:int,user_id:int,amount:int):
    async with conn() as db:
        await db.execute('INSERT OR IGNORE INTO referral_wallets(bot_id,user_id,balance,created_at) VALUES(?,?,0,?)',(bot_id,user_id,int(time.time())))
        await db.execute('UPDATE referral_wallets SET balance=COALESCE(balance,0)+? WHERE bot_id=? AND user_id=?',(int(amount),bot_id,user_id))
        await db.commit()

async def take_referral_balance(bot_id:int,user_id:int,amount:int):
    amount=int(amount)
    if amount <= 0:
        return True
    async with conn() as db:
        await db.execute('BEGIN IMMEDIATE')
        await db.execute('INSERT OR IGNORE INTO referral_wallets(bot_id,user_id,balance,created_at) VALUES(?,?,0,?)',(bot_id,user_id,int(time.time())))
        cur=await db.execute('UPDATE referral_wallets SET balance=balance-? WHERE bot_id=? AND user_id=? AND balance>=?',(amount,bot_id,user_id,amount))
        await db.commit()
        return cur.rowcount > 0

async def child_ref_count(bot_id:int,user_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(*) c FROM users WHERE ref_by=?',(user_id,)); return (await cur.fetchone())['c']


async def stat():
    async with conn() as db:
        out={}
        for name,table in [('users','users'),('bots','bots'),('movies','movies'),('payments','payments')]:
            cur=await db.execute(f'SELECT COUNT(*) c FROM {table}'); out[name]=(await cur.fetchone())['c']
        return out

async def upsert_pay_method(bot_id:int,name:str,value:str):
    async with conn() as db:
        r=await (await db.execute('SELECT id FROM pay_methods WHERE bot_id=? AND lower(name)=lower(?)',(bot_id,name))).fetchone()
        if r:
            await db.execute('UPDATE pay_methods SET value=?, active=1 WHERE id=? AND bot_id=?',(value,r['id'],bot_id))
        else:
            await db.execute('INSERT INTO pay_methods(bot_id,name,value,active) VALUES(?,?,?,1)',(bot_id,name,value))
        await db.commit()


async def child_user_count(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(DISTINCT user_id) c FROM movie_views WHERE bot_id=?',(bot_id,))
        return (await cur.fetchone())['c']

async def movie_view_count(bot_id:int, since:int=0):
    async with conn() as db:
        if since:
            cur=await db.execute('SELECT COUNT(*) c FROM movie_views WHERE bot_id=? AND created_at>=?',(bot_id,since))
        else:
            cur=await db.execute('SELECT COUNT(*) c FROM movie_views WHERE bot_id=?',(bot_id,))
        return (await cur.fetchone())['c']

async def payments_sum(bot_id:int, status:str='approved'):
    async with conn() as db:
        cur=await db.execute('SELECT COALESCE(SUM(amount),0) s, COUNT(*) c FROM payments WHERE bot_id=? AND status=?',(bot_id,status))
        return await cur.fetchone()

async def referral_total(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COALESCE(SUM(balance),0) s, COUNT(*) c FROM referral_wallets WHERE bot_id=?',(bot_id,))
        return await cur.fetchone()

async def channel_stats(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(*) c, COALESCE(SUM(pass_count),0) p FROM channels WHERE bot_id=?',(bot_id,))
        return await cur.fetchone()

async def ads_total_views(bot_id:int):
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(*) c, COALESCE(SUM(views),0) v FROM ads WHERE bot_id=?',(bot_id,))
        return await cur.fetchone()

async def clean_expired_premium(bot_id:int):
    async with conn() as db:
        cur=await db.execute('DELETE FROM premium WHERE bot_id=? AND until_ts<=?',(bot_id,int(time.time())))
        await db.commit(); return cur.rowcount

# =========================
# MAIN PLATFORM TARIFFS
# =========================
async def ensure_platform_tables():
    async with conn() as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS platform_tariffs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            monthly_price INTEGER,
            daily_limit INTEGER,
            speed TEXT DEFAULT '~0.5s',
            active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )""")
        for q in [
            "ALTER TABLE bots ADD COLUMN platform_tariff_id INTEGER DEFAULT 0",
            "ALTER TABLE bots ADD COLUMN platform_until INTEGER DEFAULT 0",
            "ALTER TABLE bots ADD COLUMN daily_limit INTEGER DEFAULT 300",
            "ALTER TABLE bots ADD COLUMN auto_paused INTEGER DEFAULT 0",
            "ALTER TABLE bots ADD COLUMN warned_limit_date TEXT DEFAULT ''",
        ]:
            try: await db.execute(q)
            except Exception: pass
        c=(await (await db.execute('SELECT COUNT(*) c FROM platform_tariffs')).fetchone())['c']
        if c==0:
            defaults=[
                ('🚀 Start',9000,300,'~0.5s',1),
                ('⭐ Standard',18000,1000,'~0.4s',2),
                ('💎 Pro 🔥',35000,3000,'~0.3s',3),
                ('⚡ Turbo',65000,7500,'~0.2s',4),
                ('🔥 Ultra',90000,15000,'~0.1s',5),
                ('♾️ Unlimited',150000,0,'~0s',6),
            ]
            await db.executemany('INSERT INTO platform_tariffs(name,monthly_price,daily_limit,speed,sort_order) VALUES(?,?,?,?,?)', defaults)
        await db.commit()

async def platform_tariffs(active_only=True):
    await ensure_platform_tables()
    async with conn() as db:
        q='SELECT * FROM platform_tariffs '+('WHERE active=1 ' if active_only else '')+'ORDER BY sort_order,id'
        cur=await db.execute(q); return await cur.fetchall()

async def platform_tariff_by_id(tid:int):
    await ensure_platform_tables()
    async with conn() as db:
        cur=await db.execute('SELECT * FROM platform_tariffs WHERE id=?',(tid,)); return await cur.fetchone()

async def add_platform_tariff(name, monthly_price, daily_limit, speed='~0.5s'):
    await ensure_platform_tables()
    async with conn() as db:
        mx=(await (await db.execute('SELECT COALESCE(MAX(sort_order),0) m FROM platform_tariffs')).fetchone())['m']
        await db.execute('INSERT INTO platform_tariffs(name,monthly_price,daily_limit,speed,sort_order) VALUES(?,?,?,?,?)',(name,int(monthly_price),int(daily_limit),speed,int(mx)+1)); await db.commit()

async def update_platform_tariff(tid:int, field:str, value):
    if field not in {'name','monthly_price','daily_limit','speed','active'}: return False
    await ensure_platform_tables()
    if field in {'monthly_price','daily_limit','active'}: value=int(value)
    async with conn() as db:
        await db.execute(f'UPDATE platform_tariffs SET {field}=? WHERE id=?',(value,int(tid))); await db.commit(); return True

async def delete_platform_tariff(tid:int):
    await ensure_platform_tables()
    async with conn() as db:
        await db.execute('UPDATE platform_tariffs SET active=0 WHERE id=?',(int(tid),)); await db.commit()

async def set_bot_platform(bot_id:int, tariff_id:int, days:int=30):
    t=await platform_tariff_by_id(tariff_id)
    if not t: return False
    until=int(time.time())+int(days)*86400
    async with conn() as db:
        await db.execute('UPDATE bots SET platform_tariff_id=?, platform_until=?, daily_limit=?, auto_paused=0, status=? WHERE id=?',(int(tariff_id),until,int(t['daily_limit']),'active',int(bot_id)))
        await db.commit(); return True

async def platform_daily_active(bot_id:int):
    since=int(time.time())-86400
    async with conn() as db:
        cur=await db.execute('SELECT COUNT(DISTINCT user_id) c FROM movie_views WHERE bot_id=? AND created_at>=?',(int(bot_id),since)); return (await cur.fetchone())['c']

async def platform_limit_ok(bot_id:int, user_id:int=None):
    r=await bot_by_id(bot_id)
    if not r: return False,0,0,None
    now=int(time.time())
    until=int(r['platform_until'] or 0) if 'platform_until' in r.keys() else 0
    if until and now > until:
        return False,0,int(r['daily_limit'] or 0),r
    if r['status'] != 'active':
        return False,0,int(r['daily_limit'] or 0),r
    limit=int(r['daily_limit'] or 0)
    if limit<=0: return True,0,limit,r
    used=await platform_daily_active(bot_id)
    return used < limit, used, limit, r

async def auto_pause_limit(bot_id:int, reason:str='limit'):
    async with conn() as db:
        today=time.strftime('%Y-%m-%d')
        await db.execute('UPDATE bots SET status=?, auto_paused=1, warned_limit_date=? WHERE id=?',('paused',today,int(bot_id)))
        await db.commit()

async def should_warn_limit(bot_id:int):
    r=await bot_by_id(bot_id)
    today=time.strftime('%Y-%m-%d')
    if not r: return False
    return (r['warned_limit_date'] or '') != today

async def record_runtime_event(bot_id:int, level:str, event:str, details:str=''):
    async with conn() as db:
        await db.execute('INSERT INTO runtime_events(bot_id,level,event,details,created_at) VALUES(?,?,?,?,?)',(int(bot_id or 0),level,event,details[:1000],int(time.time())))
        await db.commit()

async def should_send_movie_ad(bot_id:int, user_id:int, interval:int=3):
    interval=max(1,int(interval or 1))
    since=int(time.time())-86400
    async with conn() as db:
        r=await (await db.execute('SELECT COUNT(*) c FROM movie_views WHERE bot_id=? AND user_id=? AND created_at>=?',(bot_id,user_id,since))).fetchone()
        seen=int(r['c'] if r else 0)
        return seen % interval == 0

async def record_ad_delivery(bot_id:int,user_id:int,ad_id:int):
    async with conn() as db:
        await db.execute('INSERT INTO ad_deliveries(bot_id,user_id,ad_id,delivered_at) VALUES(?,?,?,?)',(bot_id,user_id,ad_id,int(time.time())))
        await db.commit()
