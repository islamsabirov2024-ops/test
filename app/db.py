import sqlite3
import time
from contextlib import contextmanager
from .config import DATABASE_PATH, DEFAULT_CARD, DEFAULT_PRICE

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  first_name TEXT,
  username TEXT,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS bots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL,
  bot_type TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  username TEXT,
  title TEXT,
  status TEXT DEFAULT 'pending',
  paid_until INTEGER DEFAULT 0,
  card_number TEXT DEFAULT '',
  card_holder TEXT DEFAULT '',
  price INTEGER DEFAULT 30000,
  add_required INTEGER DEFAULT 5,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  owner_id INTEGER NOT NULL,
  bot_id INTEGER,
  status TEXT DEFAULT 'pending',
  file_id TEXT,
  amount INTEGER DEFAULT 0,
  created_at INTEGER
);
CREATE TABLE IF NOT EXISTS movies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  code TEXT NOT NULL,
  file_id TEXT,
  caption TEXT,
  is_premium INTEGER DEFAULT 0,
  created_at INTEGER,
  UNIQUE(bot_id, code)
);
CREATE TABLE IF NOT EXISTS channels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bot_id INTEGER NOT NULL,
  title TEXT,
  chat_id TEXT,
  link TEXT,
  checkable INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS bot_admins (
  bot_id INTEGER NOT NULL,
  user_id INTEGER NOT NULL,
  PRIMARY KEY(bot_id, user_id)
);
CREATE TABLE IF NOT EXISTS cleaner_settings (
  bot_id INTEGER PRIMARY KEY,
  add_required INTEGER DEFAULT 5,
  mute_seconds INTEGER DEFAULT 30
);
"""

@contextmanager
def conn():
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()

def init_db():
    with conn() as db:
        db.executescript(SCHEMA)

def add_user(user):
    with conn() as db:
        db.execute("INSERT OR IGNORE INTO users(user_id,first_name,username,created_at) VALUES(?,?,?,?)",
                   (user.id, user.first_name or '', user.username or '', int(time.time())))

def create_bot(owner_id, bot_type, token, username='', title=''):
    with conn() as db:
        cur = db.execute("INSERT INTO bots(owner_id,bot_type,token,username,title,status,card_number,price,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                         (owner_id, bot_type, token, username, title, 'pending_payment', DEFAULT_CARD, DEFAULT_PRICE, int(time.time())))
        bot_id = cur.lastrowid
        db.execute("INSERT OR IGNORE INTO bot_admins(bot_id,user_id) VALUES(?,?)", (bot_id, owner_id))
        if bot_type == 'cleaner':
            db.execute("INSERT OR IGNORE INTO cleaner_settings(bot_id,add_required,mute_seconds) VALUES(?,?,?)", (bot_id, 5, 30))
        return bot_id

def list_user_bots(owner_id):
    with conn() as db:
        return db.execute("SELECT * FROM bots WHERE owner_id=? ORDER BY id DESC", (owner_id,)).fetchall()

def list_all_bots():
    with conn() as db:
        return db.execute("SELECT * FROM bots ORDER BY id DESC").fetchall()

def get_bot(bot_id):
    with conn() as db:
        return db.execute("SELECT * FROM bots WHERE id=?", (bot_id,)).fetchone()

def get_bot_by_token(token):
    with conn() as db:
        return db.execute("SELECT * FROM bots WHERE token=?", (token,)).fetchone()

def update_bot_status(bot_id, status, days=30):
    paid_until = int(time.time()) + days * 86400 if status == 'active' else 0
    with conn() as db:
        db.execute("UPDATE bots SET status=?, paid_until=? WHERE id=?", (status, paid_until, bot_id))

def update_bot_card(bot_id, card_number, card_holder):
    with conn() as db:
        db.execute("UPDATE bots SET card_number=?, card_holder=? WHERE id=?", (card_number, card_holder, bot_id))

def update_bot_price(bot_id, price):
    with conn() as db:
        db.execute("UPDATE bots SET price=? WHERE id=?", (price, bot_id))

def add_payment(owner_id, bot_id, file_id, amount):
    with conn() as db:
        cur = db.execute("INSERT INTO payments(owner_id,bot_id,file_id,amount,status,created_at) VALUES(?,?,?,?,?,?)",
                         (owner_id, bot_id, file_id, amount, 'pending', int(time.time())))
        return cur.lastrowid

def list_payments(status='pending'):
    with conn() as db:
        return db.execute("SELECT p.*, b.username, b.bot_type FROM payments p LEFT JOIN bots b ON b.id=p.bot_id WHERE p.status=? ORDER BY p.id DESC", (status,)).fetchall()

def set_payment_status(payment_id, status):
    with conn() as db:
        db.execute("UPDATE payments SET status=? WHERE id=?", (status, payment_id))

def add_movie(bot_id, code, file_id, caption='', is_premium=0):
    with conn() as db:
        db.execute("INSERT OR REPLACE INTO movies(bot_id,code,file_id,caption,is_premium,created_at) VALUES(?,?,?,?,?,?)",
                   (bot_id, str(code).lower().strip(), file_id, caption, is_premium, int(time.time())))

def get_movie(bot_id, code):
    with conn() as db:
        return db.execute("SELECT * FROM movies WHERE bot_id=? AND code=?", (bot_id, str(code).lower().strip())).fetchone()

def movie_count(bot_id):
    with conn() as db:
        return db.execute("SELECT COUNT(*) c FROM movies WHERE bot_id=?", (bot_id,)).fetchone()['c']

def add_channel(bot_id, title, chat_id, link, checkable=1):
    with conn() as db:
        db.execute("INSERT INTO channels(bot_id,title,chat_id,link,checkable) VALUES(?,?,?,?,?)", (bot_id,title,chat_id,link,checkable))

def list_channels(bot_id):
    with conn() as db:
        return db.execute("SELECT * FROM channels WHERE bot_id=?", (bot_id,)).fetchall()

def is_bot_admin(bot_id, user_id):
    with conn() as db:
        row = db.execute("SELECT 1 FROM bot_admins WHERE bot_id=? AND user_id=?", (bot_id, user_id)).fetchone()
        return bool(row)

def get_cleaner_settings(bot_id):
    with conn() as db:
        row = db.execute("SELECT * FROM cleaner_settings WHERE bot_id=?", (bot_id,)).fetchone()
        return row

def set_cleaner_add_required(bot_id, n):
    with conn() as db:
        db.execute("INSERT OR IGNORE INTO cleaner_settings(bot_id,add_required,mute_seconds) VALUES(?,?,?)", (bot_id,5,30))
        db.execute("UPDATE cleaner_settings SET add_required=? WHERE bot_id=?", (n,bot_id))
