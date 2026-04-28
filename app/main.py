from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN
from app.db import init_db, list_active_bots
from app.handlers import builder
from app.runner import BotManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN yo‘q")

    await init_db()

    manager = BotManager()
    builder.set_manager(manager)

    active = await list_active_bots()
    await manager.start_many(active)

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(builder.router)

    expire_task = asyncio.create_task(builder.expire_loop(bot, manager))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        expire_task.cancel()
        await manager.stop_all()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
