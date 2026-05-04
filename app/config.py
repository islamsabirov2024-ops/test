import os
from dotenv import load_dotenv
load_dotenv()

def s(name, default=''):
    return os.getenv(name, default).strip()

def i(name, default=0):
    try: return int(s(name, str(default)) or default)
    except Exception: return default

def b(name, default=False):
    return s(name, str(default)).lower() in {'1','true','yes','on'}

BOT_TOKEN=s('BOT_TOKEN')
BOT_NAME=s('BOT_NAME','Super MultiBot')
SUPER_ADMIN_ID=i('SUPER_ADMIN_ID',5907118746)
DATABASE_PATH=s('DATABASE_PATH','data.sqlite3')
MOVIES_CHANNEL_ID=s('MOVIES_CHANNEL_ID')
SUBSCRIPTION_FAKE_VERIFY=b('SUBSCRIPTION_FAKE_VERIFY', True)
