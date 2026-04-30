import os
from dotenv import load_dotenv

load_dotenv()


def get_str(name: str, default: str = "") -> str:
    return str(os.getenv(name, default)).strip()


def get_int(name: str, default: int = 0) -> int:
    raw = get_str(name, str(default))
    try:
        return int(raw)
    except Exception:
        return default


BOT_TOKEN = get_str("BOT_TOKEN")
SUPER_ADMIN_ID = get_int("SUPER_ADMIN_ID", 5907118746)
DATABASE_PATH = get_str("DATABASE_PATH", "data.db")
PLATFORM_NAME = get_str("PLATFORM_NAME", "Super MultiBot")
DEFAULT_CARD = get_str("DEFAULT_CARD", "Karta hali qo'shilmagan")
DEFAULT_PRICE = get_int("DEFAULT_PRICE", 30000)
