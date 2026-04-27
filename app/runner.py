from __future__ import annotations
import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.modules import movie, ad_cleaner, music_finder, invite_gate, it_lessons

log=logging.getLogger(__name__)
MODULES={'movie':movie.setup,'ad_cleaner':ad_cleaner.setup,'music_finder':music_finder.setup,'invite_gate':invite_gate.setup,'it_lessons':it_lessons.setup}

class BotManager:
    def __init__(self):
        self.tasks: dict[int, asyncio.Task]={}
        self.bots: dict[int, Bot]={}
    async def start_child(self, row:dict):
        bot_id=int(row['id'])
        if bot_id in self.tasks and not self.tasks[bot_id].done():
            return True, 'Bu bot allaqachon ishlab turibdi.'
        setup=MODULES.get(row['bot_type_code'])
        if not setup: return False, 'Bot turi topilmadi.'
        async def runner():
            bot=Bot(row['bot_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            self.bots[bot_id]=bot
            dp=Dispatcher()
            setup(dp, bot_id, int(row['owner_user_id']))
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.exception('Child bot %s failed: %s', bot_id, e)
            finally:
                try: await bot.session.close()
                except Exception: pass
                self.bots.pop(bot_id, None)
        self.tasks[bot_id]=asyncio.create_task(runner())
        return True, 'Agar token boshqa serverda ishlamayotgan bo‘lsa, bot hozir javob beradi.'
    async def stop_child(self, bot_id:int):
        t=self.tasks.get(bot_id)
        if t and not t.done():
            t.cancel()
            try: await t
            except asyncio.CancelledError: pass
        self.tasks.pop(bot_id, None)
    async def start_many(self, rows):
        for r in rows:
            await self.start_child(dict(r))
    async def stop_all(self):
        for bot_id in list(self.tasks):
            await self.stop_child(bot_id)
