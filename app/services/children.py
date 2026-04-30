import asyncio
import logging
from telegram.ext import Application

from app.constants import TEMPLATE_KINO, TEMPLATE_MODERATOR, BOT_STATUS_ACTIVE
from app import database as db
from app.templates.kino_bot import setup_kino_bot
from app.templates.moderator_bot import setup_moderator_bot

log = logging.getLogger(__name__)

RUNNING = {}


# =========================
# 🤖 BUILD CHILD BOT
# =========================

async def build_child(bot_row):
    app = Application.builder().token(bot_row["token"]).build()

    app.bot_data["bot_row"] = bot_row
    app.bot_data["bot_id"] = bot_row["id"]

    if bot_row["template"] == TEMPLATE_MODERATOR:
        setup_moderator_bot(app)
    else:
        setup_kino_bot(app)

    return app


# =========================
# ▶️ START CHILD BOT
# =========================

async def start_child(bot_row):
    bot_id = bot_row["id"]

    if bot_id in RUNNING:
        return True

    try:
        app = await build_child(bot_row)

        await app.initialize()
        await app.start()

        # ❗ NEW PTB v21 polling
        await app.bot.initialize()
        app.create_task(app.run_polling(drop_pending_updates=True))

        RUNNING[bot_id] = app
        log.info("✅ Child bot %s started", bot_id)

        return True

    except Exception as e:
        log.exception("❌ Child start failed: %s", bot_id)
        return False


# =========================
# ⏸ STOP CHILD BOT
# =========================

async def stop_child(bot_id: int):
    app = RUNNING.pop(bot_id, None)

    if not app:
        return

    try:
        await app.stop()
        await app.shutdown()
        log.info("⏸ Child bot %s stopped", bot_id)

    except Exception:
        log.exception("Stop error: %s", bot_id)


# =========================
# 🔄 SYNC CHILDREN
# =========================

async def sync_children():
    bots = await db.list_bots()

    active_ids = set()

    for b in bots:
        if b["status"] == BOT_STATUS_ACTIVE:
            active_ids.add(b["id"])

            if b["id"] not in RUNNING:
                await start_child(b)

    for bot_id in list(RUNNING.keys()):
        if bot_id not in active_ids:
            await stop_child(bot_id)


# =========================
# 🔁 LOOP
# =========================

async def sync_loop():
    while True:
        try:
            await sync_children()
        except Exception:
            log.exception("sync error")

        await asyncio.sleep(10)
