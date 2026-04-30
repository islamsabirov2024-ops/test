import os
from dotenv import load_dotenv

load_dotenv()


def _str(name: str, default: str = "") -> str:
    return str(os.getenv(name, default)).strip()


def _int(name: str, default: int = 0) -> int:
    try:
        return int(_str(name, str(default)) or default)
    except Exception:
        return default

BOT_TOKEN = _str("BOT_TOKEN")
SUPER_ADMIN_ID = _int("SUPER_ADMIN_ID", 0)
DATABASE_PATH = _str("DATABASE_PATH", "data.db")
LOG_LEVEL = _str("LOG_LEVEL", "INFO")
