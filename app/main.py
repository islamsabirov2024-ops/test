from __future__ import annotations
import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.config import BOT_TOKEN
from app.db import init_db, list_active_bots
from app.handlers import builder
from app.runner import BotManager
logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN kiritilmagan. Render ENV yoki .env ga yozing.')
    await init_db(); mgr=BotManager(); builder.set_manager(mgr)
    await mgr.start_many(await list_active_bots())
    bot=Bot(BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML)); dp=Dispatcher(); dp.include_router(builder.router)
    exp=asyncio.create_task(builder.expire_loop(bot,mgr))
    try: await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
    finally:
        exp.cancel(); await mgr.stop_all(); await bot.session.close()
if __name__=='__main__': asyncio.run(main())
