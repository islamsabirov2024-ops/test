import logging
import os
from typing import Any, Iterable

import asyncpg

from config import SUPER_ADMIN_ID

logger = logging.getLogger(__name__)
pool: asyncpg.Pool | None = None

def _schema_name() -> str:
    raw = os.getenv('BOT_SCHEMA', '').strip()
    if not raw:
        return ''
    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in raw)
    if safe and safe[0].isdigit():
        safe = 'b_' + safe
    return safe[:48]



def _clean(value: str | None) -> str:
    return (value or "").replace("\n", "").replace("\r", "").strip()


def get_database_config() -> dict[str, Any]:
    database_url = _clean(os.getenv("DATABASE_URL"))
    database_public_url = _clean(os.getenv("DATABASE_PUBLIC_URL"))
    if database_url:
        return {"dsn": database_url}
    if database_public_url:
        return {"dsn": database_public_url}
    pghost = _clean(os.getenv("PGHOST"))
    pgport = _clean(os.getenv("PGPORT")) or "5432"
    pguser = _clean(os.getenv("PGUSER"))
    pgpassword = _clean(os.getenv("PGPASSWORD"))
    pgdatabase = _clean(os.getenv("PGDATABASE")) or _clean(os.getenv("POSTGRES_DB"))
    if pghost and pguser and pgdatabase:
        return {"host": pghost, "port": int(pgport), "user": pguser, "password": pgpassword, "database": pgdatabase}
    raise RuntimeError("Database config topilmadi.")


async def connect_db() -> asyncpg.Pool | None:
    global pool
    if pool is not None:
        return pool
    cfg = get_database_config()
    try:
        schema = _schema_name()
        if schema:
            # Har bir mijoz kino boti o‘z schema'sida ishlaydi: movies, settings, tariffs aralashib ketmaydi.
            if "dsn" in cfg:
                pool = await asyncpg.create_pool(
                    dsn=_clean(cfg["dsn"]), min_size=1, max_size=10, command_timeout=60,
                    server_settings={"search_path": schema + ",public"},
                )
            else:
                pool = await asyncpg.create_pool(
                    **cfg, min_size=1, max_size=10, command_timeout=60,
                    server_settings={"search_path": schema + ",public"},
                )
            async with pool.acquire() as conn:
                await conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
                await conn.execute(f'SET search_path TO "{schema}", public')
        else:
            if "dsn" in cfg:
                pool = await asyncpg.create_pool(dsn=_clean(cfg["dsn"]), min_size=1, max_size=10, command_timeout=60)
            else:
                pool = await asyncpg.create_pool(**cfg, min_size=1, max_size=10, command_timeout=60)
        return pool
    except Exception:
        logger.exception("❌ Database ulanish xatosi")
        return None


async def execute(query: str, params: Iterable[Any] = ()):
    db = await connect_db()
    if not db:
        raise RuntimeError("Database ulanmagan")
    async with db.acquire() as conn:
        return await conn.execute(query, *tuple(params))


async def fetchone(query: str, params: Iterable[Any] = ()):
    db = await connect_db()
    if not db:
        return None
    async with db.acquire() as conn:
        row = await conn.fetchrow(query, *tuple(params))
        return dict(row) if row else None


async def fetchall(query: str, params: Iterable[Any] = ()):
    db = await connect_db()
    if not db:
        return []
    async with db.acquire() as conn:
        rows = await conn.fetch(query, *tuple(params))
        return [dict(r) for r in rows]


async def fetchval(query: str, params: Iterable[Any] = (), default: Any = None):
    db = await connect_db()
    if not db:
        return default
    async with db.acquire() as conn:
        value = await conn.fetchval(query, *tuple(params))
        return default if value is None else value


def normalize_movie_code(code: str) -> str:
    return str(code or "").strip().lower()


def is_external_social_link(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    return any(x in raw for x in ("instagram.com", "youtube.com", "youtu.be", "tiktok.com", "facebook.com", "x.com", "twitter.com"))


def normalize_channel_link(link: str | None) -> str:
    raw = str(link or "").strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        return f"https://t.me/{raw[1:]}"
    if raw.startswith(("https://", "http://")):
        return raw
    if raw.startswith("t.me/"):
        return f"https://{raw}"
    return f"https://t.me/{raw}"




def is_supported_telegram_link(value: str | None) -> bool:
    raw = str(value or "").strip().lower()
    if not raw:
        return False
    if raw.startswith("@"):
        return True
    if raw.startswith(("https://t.me/", "http://t.me/", "t.me/")):
        return "/+" not in raw and "joinchat" not in raw
    return "." not in raw and "/" not in raw and " " not in raw

def normalize_channel_username(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw or is_external_social_link(raw):
        return ""
    if raw.startswith("@"):
        raw = raw[1:]
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if raw.startswith(prefix):
            raw = raw.replace(prefix, "", 1).strip("/")
    if "joinchat" in raw.lower() or raw.startswith("+"):
        return ""
    if "/" in raw:
        raw = raw.split("/", 1)[0].strip()
    if " " in raw or "." in raw:
        return ""
    return raw


async def init_db():
    db = await connect_db()
    if not db:
        return
    async with db.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_expire TIMESTAMPTZ NULL,
            balance INTEGER DEFAULT 0,
            joined_at TIMESTAMPTZ DEFAULT NOW(),
            last_active TIMESTAMPTZ DEFAULT NOW(),
            referred_by BIGINT NULL
        );
        CREATE TABLE IF NOT EXISTS admins (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS channels (
            id BIGSERIAL PRIMARY KEY,
            channel_id TEXT UNIQUE NOT NULL,
            channel_username TEXT DEFAULT '',
            channel_name TEXT,
            channel_link TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS promo_links (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tariffs (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            price INTEGER NOT NULL,
            description TEXT DEFAULT '',
            is_vip INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS payments (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            tariff_id BIGINT NULL,
            amount INTEGER NOT NULL,
            screenshot_file_id TEXT,
            note TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            reject_reason TEXT DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            reviewed_at TIMESTAMPTZ NULL,
            reviewed_by BIGINT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS referrals (
            id BIGSERIAL PRIMARY KEY,
            inviter_id BIGINT NOT NULL,
            invited_id BIGINT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id BIGSERIAL PRIMARY KEY,
            inviter_id BIGINT NOT NULL,
            referrals_count INTEGER NOT NULL,
            reward_days INTEGER NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS movies (
            id BIGSERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT DEFAULT '',
            source_chat_id TEXT DEFAULT '',
            source_message_id BIGINT DEFAULT 0,
            source_kind TEXT DEFAULT 'copy',
            source_file_id TEXT DEFAULT '',
            source_file_type TEXT DEFAULT '',
            source_url TEXT DEFAULT '',
            is_premium INTEGER DEFAULT 0,
            views BIGINT DEFAULT 0,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            is_active INTEGER DEFAULT 1
        );
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS source_kind TEXT DEFAULT 'copy';
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS source_file_id TEXT DEFAULT '';
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS source_file_type TEXT DEFAULT '';
        ALTER TABLE movies ADD COLUMN IF NOT EXISTS source_url TEXT DEFAULT '';
        """)
        defaults = [
            ("welcome_message", "🎬 Assalomu alaykum, {name}!\\n\\nKino kodini yuboring."),
            ("subscription_required", "1"),
            ("subscription_fake_verify", "0"),
            ("payment_card", "8600 0000 0000 0000"),
            ("payment_note", "To'lov qilgach screenshot yuboring. Admin tasdiqlaydi."),
            ("premium_enabled", "1"),
            ("referral_enabled", "1"),
            ("referral_price", "200"),
            ("bot_name", "Kino Bot"),
            ("movie_sharing_enabled", "1"),
        ]
        for key, value in defaults:
            await conn.execute("INSERT INTO settings(key, value) VALUES ($1, $2) ON CONFLICT (key) DO NOTHING", key, value)
        if SUPER_ADMIN_ID:
            await conn.execute("INSERT INTO admins(user_id, username, full_name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO NOTHING", int(SUPER_ADMIN_ID), "superadmin", "Super Admin")


async def cleanup_expired_premium():
    await execute("UPDATE users SET is_premium=0 WHERE is_premium=1 AND premium_expire IS NOT NULL AND premium_expire <= NOW()")


async def get_setting(key: str, default: str | None = None):
    row = await fetchone("SELECT value FROM settings WHERE key=$1", (key,))
    return row["value"] if row else default


async def set_setting(key: str, value: str):
    await execute("INSERT INTO settings(key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (key, value))
    return True


async def add_or_update_user(user_id: int, username: str | None, full_name: str, referred_by: int | None = None):
    existing = await fetchone("SELECT * FROM users WHERE user_id=$1", (user_id,))
    if existing:
        await execute("UPDATE users SET username=$1, full_name=$2, last_active=NOW(), referred_by=COALESCE(referred_by, $4) WHERE user_id=$3", (username, full_name, user_id, referred_by))
        return False
    await execute("INSERT INTO users(user_id, username, full_name, referred_by) VALUES ($1, $2, $3, $4)", (user_id, username, full_name, referred_by))
    return True


async def get_user(user_id: int):
    await cleanup_expired_premium()
    return await fetchone("SELECT * FROM users WHERE user_id=$1", (user_id,))


async def get_user_balance(user_id: int) -> int:
    return int(await fetchval("SELECT COALESCE(balance,0) FROM users WHERE user_id=$1", (user_id,), 0) or 0)


async def add_user_balance(user_id: int, amount: int):
    await execute("UPDATE users SET balance=COALESCE(balance,0)+$1 WHERE user_id=$2", (int(amount), user_id))
    return True


async def subtract_user_balance(user_id: int, amount: int):
    balance = await get_user_balance(user_id)
    if balance < int(amount):
        return False
    await execute("UPDATE users SET balance=COALESCE(balance,0)-$1 WHERE user_id=$2", (int(amount), user_id))
    return True


async def get_all_user_ids():
    rows = await fetchall("SELECT user_id FROM users")
    return [r["user_id"] for r in rows]


async def get_users_count(): return await fetchval("SELECT COUNT(*) FROM users", default=0)
async def get_today_users_count(): return await fetchval("SELECT COUNT(*) FROM users WHERE joined_at::date=CURRENT_DATE", default=0)
async def get_movies_count(): return await fetchval("SELECT COUNT(*) FROM movies WHERE is_active=1", default=0)
async def get_total_views(): return await fetchval("SELECT COALESCE(SUM(views),0) FROM movies WHERE is_active=1", default=0)


async def get_premium_users_count():
    await cleanup_expired_premium()
    return await fetchval("SELECT COUNT(*) FROM users WHERE is_premium=1 AND (premium_expire IS NULL OR premium_expire > NOW())", default=0)


async def set_user_premium(user_id: int, duration_days: int):
    await execute("""
        UPDATE users
        SET is_premium=1,
            premium_expire = CASE WHEN premium_expire IS NOT NULL AND premium_expire > NOW()
                                  THEN premium_expire + ($1 * INTERVAL '1 day')
                                  ELSE NOW() + ($1 * INTERVAL '1 day') END
        WHERE user_id=$2
    """, (int(duration_days), user_id))
    return True


async def revoke_user_premium(user_id: int):
    await execute("UPDATE users SET is_premium=0, premium_expire=NULL WHERE user_id=$1", (user_id,))
    return True


async def get_active_premium_users(limit: int = 100):
    await cleanup_expired_premium()
    return await fetchall("""
        SELECT u.user_id, u.username, u.full_name, u.premium_expire,
               EXTRACT(EPOCH FROM (u.premium_expire - NOW())) AS remaining_seconds
        FROM users u
        WHERE u.is_premium=1 AND (u.premium_expire IS NULL OR u.premium_expire > NOW())
        ORDER BY u.premium_expire DESC NULLS LAST LIMIT $1
    """, (int(limit),))


async def is_admin(user_id: int):
    if SUPER_ADMIN_ID and int(user_id) == int(SUPER_ADMIN_ID):
        return True
    return await fetchone("SELECT 1 FROM admins WHERE user_id=$1", (user_id,)) is not None


async def add_admin(user_id: int, username: str | None = None, full_name: str | None = None):
    await execute("INSERT INTO admins(user_id, username, full_name) VALUES ($1,$2,$3) ON CONFLICT (user_id) DO NOTHING", (user_id, username, full_name))
    return True


async def remove_admin(user_id: int):
    if SUPER_ADMIN_ID and int(user_id) == int(SUPER_ADMIN_ID):
        return False
    await execute("DELETE FROM admins WHERE user_id=$1", (user_id,))
    return True

async def delete_admin(user_id: int): return await remove_admin(user_id)
async def get_admins(): return await fetchall("SELECT * FROM admins ORDER BY added_at DESC")


async def add_movie(code: str, title: str = "", description: str = "", source_chat_id: str = "", source_message_id: int = 0,
                    is_premium: int = 0, source_kind: str = "copy", source_file_id: str = "", source_file_type: str = "", source_url: str = ""):
    normalized = normalize_movie_code(code)
    if not normalized:
        raise ValueError("code majburiy")
    await execute("""
        INSERT INTO movies(code, title, description, source_chat_id, source_message_id, source_kind, source_file_id, source_file_type, source_url, is_premium, is_active)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,1)
        ON CONFLICT (code) DO UPDATE SET
            title=EXCLUDED.title,
            description=EXCLUDED.description,
            source_chat_id=EXCLUDED.source_chat_id,
            source_message_id=EXCLUDED.source_message_id,
            source_kind=EXCLUDED.source_kind,
            source_file_id=EXCLUDED.source_file_id,
            source_file_type=EXCLUDED.source_file_type,
            source_url=EXCLUDED.source_url,
            is_premium=EXCLUDED.is_premium,
            is_active=1
    """, (normalized, str(title).strip() or normalized, str(description).strip(), str(source_chat_id).strip(), int(source_message_id or 0), source_kind, str(source_file_id or ""), str(source_file_type or ""), str(source_url or ""), int(bool(is_premium))))
    return await get_movie_by_code(normalized)


async def get_movie_by_code(code: str): return await fetchone("SELECT * FROM movies WHERE code=$1 AND is_active=1", (normalize_movie_code(code),))
async def delete_movie(code: str): await execute("UPDATE movies SET is_active=0 WHERE code=$1", (normalize_movie_code(code),)); return True
async def increment_movie_views(code: str): await execute("UPDATE movies SET views=views+1 WHERE code=$1", (normalize_movie_code(code),))
async def update_movie_code(old_code: str, new_code: str): await execute("UPDATE movies SET code=$1 WHERE code=$2 AND is_active=1", (normalize_movie_code(new_code), normalize_movie_code(old_code))); return True
async def update_movie_title(code: str, title: str): await execute("UPDATE movies SET title=$1 WHERE code=$2 AND is_active=1", (str(title).strip(), normalize_movie_code(code))); return await get_movie_by_code(code)
async def update_movie_description(code: str, description: str): await execute("UPDATE movies SET description=$1 WHERE code=$2 AND is_active=1", (str(description).strip(), normalize_movie_code(code))); return await get_movie_by_code(code)
async def update_movie_premium(code: str, is_premium: int): await execute("UPDATE movies SET is_premium=$1 WHERE code=$2 AND is_active=1", (int(bool(is_premium)), normalize_movie_code(code))); return await get_movie_by_code(code)


async def add_channel(channel_id: str = "", channel_name: str = "", channel_link: str = "", channel_username: str = ""):
    clean_id = str(channel_id or "").strip()
    raw_link = str(channel_link or "").strip()
    raw_username = str(channel_username or "").strip()

    if raw_link and is_external_social_link(raw_link):
        raise ValueError("Instagram/YouTube kabi linklar majburiy obunaga qo'shilmaydi. Ularni reklama link sifatida qo'shing.")
    if raw_link and not is_supported_telegram_link(raw_link):
        raise ValueError("Majburiy obuna uchun faqat public Telegram link yoki @username ishlatiladi.")
    if raw_username and is_external_social_link(raw_username):
        raise ValueError("Tashqi ijtimoiy tarmoq linki kanal sifatida qo'shilmaydi.")

    clean_link = normalize_channel_link(raw_link) if raw_link else ""
    clean_username = normalize_channel_username(raw_username)
    if not clean_username and clean_id:
        clean_username = normalize_channel_username(clean_id)
    if not clean_link and clean_username:
        clean_link = normalize_channel_link(f"@{clean_username}")
    unique_id = clean_id or (f"@{clean_username}" if clean_username else clean_link)
    if not unique_id:
        raise ValueError("Kanal uchun yaroqli Telegram qiymat topilmadi.")
    await execute("INSERT INTO channels(channel_id, channel_username, channel_name, channel_link, is_active) VALUES ($1,$2,$3,$4,1) ON CONFLICT (channel_id) DO UPDATE SET channel_username=EXCLUDED.channel_username, channel_name=EXCLUDED.channel_name, channel_link=EXCLUDED.channel_link, is_active=1", (unique_id, clean_username, channel_name.strip(), clean_link))
    return await fetchone("SELECT * FROM channels WHERE channel_id=$1", (unique_id,))


async def get_channels(): return await fetchall("SELECT * FROM channels WHERE is_active=1 ORDER BY added_at DESC")
async def delete_channel(channel_id: str):
    target = str(channel_id).strip(); username = normalize_channel_username(target)
    await execute("UPDATE channels SET is_active=0 WHERE channel_id=$1 OR channel_username=$2 OR channel_link=$3 OR CAST(id AS TEXT)=$4", (target, username, target, target)); return True


async def add_promo_link(title: str, url: str, sort_order: int = 0):
    return await fetchone("INSERT INTO promo_links(title,url,sort_order,is_active) VALUES ($1,$2,$3,1) RETURNING *", (title.strip(), url.strip(), int(sort_order)))
async def get_promo_links(): return await fetchall("SELECT * FROM promo_links WHERE is_active=1 ORDER BY sort_order ASC, id ASC")
async def delete_promo_link(promo_id_or_url: int | str):
    target = str(promo_id_or_url).strip()
    if target.isdigit():
        await execute("UPDATE promo_links SET is_active=0 WHERE id=$1", (int(target),))
    else:
        await execute("UPDATE promo_links SET is_active=0 WHERE url=$1", (target,))
    return True


async def add_tariff(name: str, duration_days: int, price: int, description: str = "", is_vip: int = 0):
    return await fetchone("INSERT INTO tariffs(name,duration_days,price,description,is_vip,is_active) VALUES ($1,$2,$3,$4,$5,1) RETURNING *", (name.strip(), int(duration_days), int(price), description.strip(), int(bool(is_vip))))
async def get_tariffs(): return await fetchall("SELECT * FROM tariffs WHERE is_active=1 ORDER BY is_vip DESC, price ASC, id DESC")
async def get_tariff(tariff_id: int): return await fetchone("SELECT * FROM tariffs WHERE id=$1 AND is_active=1", (int(tariff_id),))
async def delete_tariff(tariff_id: int): await execute("UPDATE tariffs SET is_active=0 WHERE id=$1", (int(tariff_id),)); return True


async def add_payment(user_id: int, tariff_id: int | None, amount: int, screenshot_file_id: str | None = None, note: str = ""):
    return await fetchone("INSERT INTO payments(user_id,tariff_id,amount,screenshot_file_id,note,status) VALUES ($1,$2,$3,$4,$5,'pending') RETURNING *", (user_id, tariff_id, int(amount), screenshot_file_id, note))


async def get_pending_payments():
    return await fetchall("""
        SELECT p.*, u.username, u.full_name, t.name AS tariff_name, t.duration_days, t.is_vip
        FROM payments p
        LEFT JOIN users u ON u.user_id=p.user_id
        LEFT JOIN tariffs t ON t.id=p.tariff_id
        WHERE p.status='pending' ORDER BY p.created_at ASC
    """)


async def approve_payment(payment_id: int, admin_id: int):
    payment = await fetchone("SELECT * FROM payments WHERE id=$1 AND status='pending'", (int(payment_id),))
    if not payment:
        return None
    await execute("UPDATE payments SET status='approved', reviewed_at=NOW(), reviewed_by=$1 WHERE id=$2", (admin_id, int(payment_id)))
    if payment.get("tariff_id"):
        tariff = await get_tariff(int(payment["tariff_id"]))
        if tariff:
            await set_user_premium(int(payment["user_id"]), int(tariff["duration_days"]))
    return await fetchone("SELECT p.*, t.name AS tariff_name, t.duration_days, t.is_vip FROM payments p LEFT JOIN tariffs t ON t.id=p.tariff_id WHERE p.id=$1", (int(payment_id),))


async def reject_payment(payment_id: int, admin_id: int, reason: str = ""):
    payment = await fetchone("SELECT * FROM payments WHERE id=$1 AND status='pending'", (int(payment_id),))
    if not payment:
        return None
    await execute("UPDATE payments SET status='rejected', reviewed_at=NOW(), reviewed_by=$1, reject_reason=$2 WHERE id=$3", (admin_id, reason.strip(), int(payment_id)))
    return await fetchone("SELECT * FROM payments WHERE id=$1", (int(payment_id),))


async def is_referral_enabled() -> bool: return str(await get_setting("referral_enabled", "1")) == "1"
async def get_referral_price() -> int: return int(await fetchval("SELECT COALESCE(value,'200')::int FROM settings WHERE key='referral_price'", default=200) or 200)


async def add_referral(inviter_id: int, invited_id: int):
    if inviter_id == invited_id:
        return False
    existing = await fetchone("SELECT 1 FROM referrals WHERE invited_id=$1", (invited_id,))
    if existing:
        return False
    await execute("INSERT INTO referrals(inviter_id, invited_id) VALUES ($1,$2)", (inviter_id, invited_id))
    if await is_referral_enabled():
        await add_user_balance(inviter_id, await get_referral_price())
    return True


async def get_referral_count(inviter_id: int): return await fetchval("SELECT COUNT(*) FROM referrals WHERE inviter_id=$1", (inviter_id,), 0)
async def has_reward_claimed(inviter_id: int, referrals_count: int): return await fetchone("SELECT 1 FROM referral_rewards WHERE inviter_id=$1 AND referrals_count=$2", (inviter_id, referrals_count)) is not None
async def add_referral_reward(inviter_id: int, referrals_count: int, reward_days: int): await execute("INSERT INTO referral_rewards(inviter_id, referrals_count, reward_days) VALUES ($1,$2,$3)", (inviter_id, referrals_count, reward_days))


async def can_buy_tariff_with_balance(user_id: int, tariff_id: int) -> bool:
    tariff = await get_tariff(int(tariff_id))
    if not tariff:
        return False
    return await get_user_balance(user_id) >= int(tariff["price"])


async def buy_tariff_with_balance(user_id: int, tariff_id: int):
    tariff = await get_tariff(int(tariff_id))
    if not tariff:
        return None
    amount = int(tariff["price"])
    if not await subtract_user_balance(user_id, amount):
        return None
    await set_user_premium(user_id, int(tariff["duration_days"]))
    return {"user_id": user_id, "tariff_id": int(tariff["id"]), "tariff_name": tariff["name"], "duration_days": int(tariff["duration_days"]), "amount": amount, "remaining_balance": await get_user_balance(user_id)}


async def get_stats():
    await cleanup_expired_premium()
    return {
        "users": await get_users_count(),
        "today_users": await get_today_users_count(),
        "premium_users": await get_premium_users_count(),
        "movies": await get_movies_count(),
        "views": await get_total_views(),
        "channels": await fetchval("SELECT COUNT(*) FROM channels WHERE is_active=1", default=0),
        "promos": await fetchval("SELECT COUNT(*) FROM promo_links WHERE is_active=1", default=0),
        "pending_payments": await fetchval("SELECT COUNT(*) FROM payments WHERE status='pending'", default=0),
    }

# ==================================================================
# REFERRAL STATISTICS & CLEANUP HELPERS
# ==================================================================

async def get_referral_stats() -> dict:
    """Umumiy referral statistikasi: jami taklif, faol takliflovchilar, bonuslar."""
    total_referrals = await fetchval("SELECT COUNT(*) FROM referrals", default=0) or 0
    active_referrers = await fetchval("SELECT COUNT(DISTINCT inviter_id) FROM referrals", default=0) or 0
    total_rewards_paid = await fetchval("SELECT COUNT(*) FROM referral_rewards", default=0) or 0
    total_reward_days = await fetchval("SELECT COALESCE(SUM(reward_days),0) FROM referral_rewards", default=0) or 0
    price = await get_referral_price()
    total_bonus_paid = int(total_referrals) * int(price)
    return {
        "total_referrals": int(total_referrals),
        "active_referrers": int(active_referrers),
        "total_rewards_paid": int(total_rewards_paid),
        "total_reward_days": int(total_reward_days),
        "total_bonus_paid": int(total_bonus_paid),
    }


async def get_top_referrers(limit: int = 10) -> list[dict]:
    """Eng ko'p taklif qilgan foydalanuvchilar ro'yxati."""
    return await fetchall(
        """
        SELECT u.user_id, u.username, u.full_name,
               COUNT(r.id)::int AS ref_count
        FROM referrals r
        LEFT JOIN users u ON u.user_id = r.inviter_id
        GROUP BY u.user_id, u.username, u.full_name
        ORDER BY ref_count DESC, u.user_id ASC
        LIMIT $1
        """,
        (int(limit),),
    ) or []


async def cleanup_left_users() -> int:
    """180 kundan beri faol bo'lmagan, premium emas va balansi 0 bo'lgan foydalanuvchilarni o'chiradi."""
    rows = await fetchall(
        """
        DELETE FROM users
        WHERE COALESCE(is_premium,0) = 0
          AND COALESCE(balance,0) = 0
          AND last_active < NOW() - INTERVAL '180 days'
        RETURNING user_id
        """
    )
    return len(rows or [])


async def cleanup_cache_data() -> dict:
    """30 kundan eski rad etilgan to'lovlar va eskirgan referral mukofot yozuvlarini tozalaydi."""
    payments_rows = await fetchall(
        "DELETE FROM payments WHERE status='rejected' AND created_at < NOW() - INTERVAL '30 days' RETURNING id"
    )
    rewards_rows = await fetchall(
        "DELETE FROM referral_rewards WHERE created_at < NOW() - INTERVAL '180 days' RETURNING id"
    )
    return {
        "payments_removed": len(payments_rows or []),
        "rewards_removed": len(rewards_rows or []),
    }
