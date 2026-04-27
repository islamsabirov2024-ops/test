import os


def _get_str(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return str(value).strip()


def _get_int(name: str, default: int = 0) -> int:
    raw = str(os.getenv(name, default)).strip()
    try:
        return int(raw)
    except Exception:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, str(default))).strip().lower()
    return raw in {"1", "true", "yes", "on"}


BOT_TOKEN = _get_str("CHILD_BOT_TOKEN") or _get_str("BOT_TOKEN")
BOT_NAME = _get_str("CHILD_BOT_NAME") or _get_str("BOT_NAME", "Kino Bot")
BOT_USERNAME = _get_str("BOT_USERNAME")
BOT_VERSION = _get_str("BOT_VERSION", "2.1.0")
SUPER_ADMIN_ID = _get_int("CHILD_SUPER_ADMIN_ID", _get_int("SUPER_ADMIN_ID", 0))

HOST = _get_str("HOST", "0.0.0.0")
PORT = _get_int("PORT", 8080)
DEFAULT_LANGUAGE = _get_str("DEFAULT_LANGUAGE", "uz")

USE_WEBHOOK = _get_bool("USE_WEBHOOK", False)
WEBHOOK_BASE_URL = _get_str("WEBHOOK_BASE_URL")
WEBHOOK_PATH = _get_str("WEBHOOK_PATH", "/webhook")
WEBHOOK_SECRET = _get_str("WEBHOOK_SECRET")

REFERRAL_BONUS_COUNT = _get_int("REFERRAL_BONUS_COUNT", 5)
REFERRAL_BONUS_DAYS = _get_int("REFERRAL_BONUS_DAYS", 7)

DATABASE_URL = _get_str("DATABASE_URL")
DATABASE_PUBLIC_URL = _get_str("DATABASE_PUBLIC_URL")
PGHOST = _get_str("PGHOST")
PGPORT = _get_str("PGPORT", "5432")
PGUSER = _get_str("PGUSER")
PGPASSWORD = _get_str("PGPASSWORD")
PGDATABASE = _get_str("PGDATABASE")

PAYMENT_CARD = _get_str("PAYMENT_CARD")
PAYMENT_NOTE = _get_str("PAYMENT_NOTE", "To‘lovni qilib bo‘lgach, chekni rasm qilib yuboring.")

PREMIUM_ENABLED = _get_bool("PREMIUM_ENABLED", True)
SUBSCRIPTION_REQUIRED = _get_bool("SUBSCRIPTION_REQUIRED", True)
SUBSCRIPTION_FAKE_VERIFY = _get_bool("SUBSCRIPTION_FAKE_VERIFY", False)

MOVIES_CHANNEL_ID = _get_str("MOVIES_CHANNEL_ID")
MOVIES_CHANNEL_USERNAME = _get_str("MOVIES_CHANNEL_USERNAME")

LOG_LEVEL = _get_str("LOG_LEVEL", "INFO")


def build_database_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL
    if DATABASE_PUBLIC_URL:
        return DATABASE_PUBLIC_URL
    if PGHOST and PGUSER and PGDATABASE:
        return f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
    return ""


DB_DSN = build_database_url()

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN kiritilmagan")
