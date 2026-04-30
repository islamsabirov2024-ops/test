import sqlite3
import time
from contextlib import contextmanager
from app.config import DATABASE_PATH

@contextmanager
def connect():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS bots(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            bot_type TEXT NOT NULL,
            token TEXT NOT NULL,
            username TEXT DEFAULT '',
            title TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            is_paid INTEGER DEFAULT 0,
            is_running INTEGER DEFAULT 0,
            card_number TEXT DEFAULT '',
            price TEXT DEFAULT '50000',
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS movies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            title TEXT DEFAULT '',
            file_id TEXT DEFAULT '',
            source_chat_id TEXT DEFAULT '',
            source_message_id INTEGER DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            created_at INTEGER,
            UNIQUE(bot_id, code)
        );
        CREATE TABLE IF NOT EXISTS channels(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            username TEXT DEFAULT '',
            link TEXT DEFAULT '',
            checkable INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS settings(
            bot_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY(bot_id, key)
        );
        CREATE TABLE IF NOT EXISTS cleaner_groups(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            required_invites INTEGER DEFAULT 5,
            mute_seconds INTEGER DEFAULT 30,
            active INTEGER DEFAULT 1,
            UNIQUE(bot_id, chat_id)
        );
        CREATE TABLE IF NOT EXISTS invite_counts(
            bot_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY(bot_id, chat_id, user_id)
        );
        ''')

def add_user(user_id:int, full_name:str):
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO users(user_id, full_name, created_at) VALUES(?,?,?)', (user_id, full_name, int(time.time())))

def create_bot(owner_id:int, bot_type:str, token:str, username:str='', title:str='') -> int:
    with connect() as db:
        cur = db.execute('INSERT INTO bots(owner_id, bot_type, token, username, title, created_at) VALUES(?,?,?,?,?,?)', (owner_id, bot_type, token, username, title, int(time.time())))
        bot_id = cur.lastrowid
        default_settings(bot_id, db)
        return bot_id

def default_settings(bot_id:int, db=None):
    rows = {
        'mandatory_sub': 'off', 'premium': 'off', 'ads': 'off', 'fake_verify': 'off',
        'welcome_text': "👋 Assalomu alaykum!\n\n🎬 Kino kodini yuboring:",
        'cleaner_links': 'on', 'cleaner_forwards': 'on', 'cleaner_usernames': 'on'
    }
    close = False
    if db is None:
        close = True
        db = sqlite3.connect(DATABASE_PATH)
    for k, v in rows.items():
        db.execute('INSERT OR IGNORE INTO settings(bot_id,key,value) VALUES(?,?,?)', (bot_id,k,v))
    if close:
        db.commit(); db.close()

def get_setting(bot_id:int, key:str, default:str='') -> str:
    with connect() as db:
        r = db.execute('SELECT value FROM settings WHERE bot_id=? AND key=?', (bot_id,key)).fetchone()
        return r['value'] if r else default

def set_setting(bot_id:int, key:str, value:str):
    with connect() as db:
        db.execute('INSERT INTO settings(bot_id,key,value) VALUES(?,?,?) ON CONFLICT(bot_id,key) DO UPDATE SET value=excluded.value', (bot_id,key,value))

def list_bots(owner_id:int|None=None):
    with connect() as db:
        if owner_id:
            return db.execute('SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC', (owner_id,)).fetchall()
        return db.execute('SELECT * FROM bots ORDER BY id DESC').fetchall()

def get_bot(bot_id:int):
    with connect() as db:
        return db.execute('SELECT * FROM bots WHERE id=?', (bot_id,)).fetchone()

def set_bot_status(bot_id:int, status:str=None, is_paid:int|None=None, is_running:int|None=None):
    parts=[]; vals=[]
    if status is not None: parts.append('status=?'); vals.append(status)
    if is_paid is not None: parts.append('is_paid=?'); vals.append(is_paid)
    if is_running is not None: parts.append('is_running=?'); vals.append(is_running)
    if not parts: return
    vals.append(bot_id)
    with connect() as db:
        db.execute(f'UPDATE bots SET {", ".join(parts)} WHERE id=?', vals)

def set_bot_card_price(bot_id:int, card:str|None=None, price:str|None=None):
    with connect() as db:
        if card is not None: db.execute('UPDATE bots SET card_number=? WHERE id=?', (card,bot_id))
        if price is not None: db.execute('UPDATE bots SET price=? WHERE id=?', (price,bot_id))

def add_payment(bot_id:int, user_id:int, file_id:str) -> int:
    with connect() as db:
        cur=db.execute('INSERT INTO payments(bot_id,user_id,file_id,created_at) VALUES(?,?,?,?)', (bot_id,user_id,file_id,int(time.time())))
        return cur.lastrowid

def list_pending_payments():
    with connect() as db:
        return db.execute('SELECT p.*, b.username, b.bot_type, b.owner_id FROM payments p JOIN bots b ON b.id=p.bot_id WHERE p.status="pending" ORDER BY p.id DESC').fetchall()

def set_payment_status(payment_id:int, status:str):
    with connect() as db:
        db.execute('UPDATE payments SET status=? WHERE id=?', (status,payment_id))

def get_payment(payment_id:int):
    with connect() as db:
        return db.execute('SELECT * FROM payments WHERE id=?', (payment_id,)).fetchone()

def add_movie(bot_id:int, code:str, title:str='', file_id:str='', source_chat_id:str='', source_message_id:int=0, is_premium:int=0):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO movies(bot_id,code,title,file_id,source_chat_id,source_message_id,is_premium,created_at) VALUES(?,?,?,?,?,?,?,?)', (bot_id,code.lower().strip(),title,file_id,source_chat_id,source_message_id,is_premium,int(time.time())))

def get_movie(bot_id:int, code:str):
    with connect() as db:
        return db.execute('SELECT * FROM movies WHERE bot_id=? AND code=?', (bot_id,code.lower().strip())).fetchone()

def list_movies(bot_id:int):
    with connect() as db:
        return db.execute('SELECT * FROM movies WHERE bot_id=? ORDER BY id DESC LIMIT 50', (bot_id,)).fetchall()

def delete_movie(bot_id:int, movie_id:int):
    with connect() as db:
        db.execute('DELETE FROM movies WHERE bot_id=? AND id=?', (bot_id,movie_id))

def inc_movie_views(movie_id:int):
    with connect() as db:
        db.execute('UPDATE movies SET views=views+1 WHERE id=?', (movie_id,))

def add_channel(bot_id:int, title:str, link:str, username:str='', checkable:int=1):
    with connect() as db:
        db.execute('INSERT INTO channels(bot_id,title,username,link,checkable) VALUES(?,?,?,?,?)', (bot_id,title,username,link,checkable))

def list_channels(bot_id:int):
    with connect() as db:
        return db.execute('SELECT * FROM channels WHERE bot_id=? AND active=1 ORDER BY id DESC', (bot_id,)).fetchall()

def delete_channel(bot_id:int, channel_id:int):
    with connect() as db:
        db.execute('DELETE FROM channels WHERE bot_id=? AND id=?', (bot_id,channel_id))

def set_cleaner_group(bot_id:int, chat_id:str, title:str, required_invites:int=5, mute_seconds:int=30):
    with connect() as db:
        db.execute('INSERT INTO cleaner_groups(bot_id,chat_id,title,required_invites,mute_seconds) VALUES(?,?,?,?,?) ON CONFLICT(bot_id,chat_id) DO UPDATE SET title=excluded.title', (bot_id,chat_id,title,required_invites,mute_seconds))

def get_cleaner_group(bot_id:int, chat_id:str):
    with connect() as db:
        return db.execute('SELECT * FROM cleaner_groups WHERE bot_id=? AND chat_id=?', (bot_id,chat_id)).fetchone()

def set_group_invites(bot_id:int, chat_id:str, n:int):
    with connect() as db:
        db.execute('UPDATE cleaner_groups SET required_invites=? WHERE bot_id=? AND chat_id=?', (n,bot_id,chat_id))

def add_invite(bot_id:int, chat_id:str, user_id:int, count:int=1):
    with connect() as db:
        db.execute('INSERT INTO invite_counts(bot_id,chat_id,user_id,count) VALUES(?,?,?,?) ON CONFLICT(bot_id,chat_id,user_id) DO UPDATE SET count=count+excluded.count', (bot_id,chat_id,user_id,count))

def get_invites(bot_id:int, chat_id:str, user_id:int) -> int:
    with connect() as db:
        r=db.execute('SELECT count FROM invite_counts WHERE bot_id=? AND chat_id=? AND user_id=?',(bot_id,chat_id,user_id)).fetchone()
        return int(r['count']) if r else 0

def stats():
    with connect() as db:
        return {
            'users': db.execute('SELECT COUNT(*) c FROM users').fetchone()['c'],
            'bots': db.execute('SELECT COUNT(*) c FROM bots').fetchone()['c'],
            'active': db.execute('SELECT COUNT(*) c FROM bots WHERE is_running=1').fetchone()['c'],
            'paid': db.execute('SELECT COUNT(*) c FROM bots WHERE is_paid=1').fetchone()['c'],
            'payments': db.execute('SELECT COUNT(*) c FROM payments').fetchone()['c'],
        }
