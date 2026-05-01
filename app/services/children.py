import asyncio
import logging
from telegram.ext import Application
from app.constants import TEMPLATE_KINO, TEMPLATE_MODERATOR, BOT_STATUS_ACTIVE
from app import database as db
from app.templates.kino_bot import setup_kino_bot
from app.templates.moderator_bot import setup_moderator_bot

log = logging.getLogger(__name__)
RUNNING = {}
TASKS = {}

async def build_child(bot_row):
    app = Application.builder().token(bot_row['token']).build()
    app.bot_data['bot_row'] = bot_row
    app.bot_data['bot_id'] = bot_row['id']
    if bot_row['template'] == TEMPLATE_MODERATOR:
        setup_moderator_bot(app)
    else:
        setup_kino_bot(app)
    return app

async def start_child(bot_row):
    bot_id = bot_row['id']
    if bot_id in RUNNING:
        return True
    app = await build_child(bot_row)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    RUNNING[bot_id] = app
    log.info("Child bot %s started", bot_id)
    return True

async def stop_child(bot_id:int):
    app = RUNNING.pop(bot_id, None)
    if not app:
        return
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    log.info("Child bot %s stopped", bot_id)

async def sync_children():
    bots = await db.list_bots()
    active_ids = set()
    for b in bots:
        if b['status'] == BOT_STATUS_ACTIVE:
            active_ids.add(b['id'])
            if b['id'] not in RUNNING:
                try:
                    await start_child(b)
                except Exception:
                    log.exception("Child start failed: %s", b.get('id'))
    for bot_id in list(RUNNING.keys()):
        if bot_id not in active_ids:
            await stop_child(bot_id)

async def sync_loop():
    while True:
        await sync_children()
        await asyncio.sleep(10)
