import asyncio
import logging
from app.services import db
from app.bot_templates.movie_bot import build_application as build_movie
from app.bot_templates.cleaner_bot import build_application as build_cleaner

log = logging.getLogger(__name__)
RUNNING = {}
TASKS = {}

async def start_child(bot_id:int):
    if bot_id in RUNNING:
        return True, 'Bot allaqachon ishlayapti'
    bot_row = db.get_bot(bot_id)
    if not bot_row:
        return False, 'Bot topilmadi'
    if int(bot_row['is_paid']) != 1:
        return False, 'To‘lov tasdiqlanmagan'
    if bot_row['bot_type'] == 'movie':
        app = build_movie(bot_row)
    elif bot_row['bot_type'] == 'cleaner':
        app = build_cleaner(bot_row)
    else:
        return False, 'Bot turi noto‘g‘ri'
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    RUNNING[bot_id] = app
    db.set_bot_status(bot_id, status='active', is_running=1)
    return True, 'Bot ishga tushdi'

async def stop_child(bot_id:int):
    app = RUNNING.pop(bot_id, None)
    if not app:
        db.set_bot_status(bot_id, is_running=0)
        return True, 'Bot to‘xtagan edi'
    try:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
    finally:
        db.set_bot_status(bot_id, is_running=0)
    return True, 'Bot to‘xtatildi'

async def toggle_child(bot_id:int):
    if bot_id in RUNNING:
        return await stop_child(bot_id)
    return await start_child(bot_id)

async def start_all_paid():
    for b in db.list_bots():
        if int(b['is_paid']) == 1 and int(b['is_running']) == 1:
            try:
                await start_child(int(b['id']))
            except Exception as e:
                log.exception('Child start failed: %s', e)
