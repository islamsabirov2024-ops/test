import os
from dotenv import load_dotenv

load_dotenv()

def _get_str(name: str, default: str = '') -> str:
    return str(os.getenv(name, default)).strip()

def _get_int(name: str, default: int = 0) -> int:
    try:
        return int(str(os.getenv(name, default)).strip())
    except Exception:
        return default

BOT_TOKEN = _get_str('BOT_TOKEN')
SUPER_ADMIN_ID = _get_int('SUPER_ADMIN_ID', 0)
DATABASE_PATH = _get_str('DATABASE_PATH', 'data.db')
HOST = _get_str('HOST', '0.0.0.0')
PORT = _get_int('PORT', 8080)
