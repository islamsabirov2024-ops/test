from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()

def _s(name: str, default: str = '') -> str:
    return os.getenv(name, default).strip()

def _i(name: str, default: int = 0) -> int:
    try:
        return int(_s(name, str(default)) or default)
    except Exception:
        return default

BOT_TOKEN = _s('BOT_TOKEN')
SUPER_ADMIN_ID = _i('SUPER_ADMIN_ID', 0)
DB_PATH = _s('DB_PATH', 'data/app.db')
AUDD_API_TOKEN = _s('AUDD_API_TOKEN')
