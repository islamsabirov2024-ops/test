from __future__ import annotations
import asyncio, logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from app.modules import movie, ad_cleaner, music_finder, invite_gate, it_lessons
log=logging.getLogger(__name__)
MODULES={'movie':movie.setup,'ad_cleaner':ad_cleaner.setup,'music_finder':music_finder.setup,'invite_gate':invite_gate.setup,'it_lessons':it_lessons.setup}
class BotManager:
    def __init__(self): self.tasks={}; self.bots={}
    async def start_child(self,row:dict):
        bid=int(row['id'])
        if bid in self.tasks and not self.tasks[bid].done(): return True,'Bot allaqachon ishlab turibdi.'
        setup=MODULES.get(row['bot_type_code'])
        if not setup: return False,'Bot turi topilmadi.'
        async def run():
            bot=Bot(row['bot_token'],default=DefaultBotProperties(parse_mode=ParseMode.HTML)); self.bots[bid]=bot; dp=Dispatcher(); setup(dp,bid,int(row['owner_user_id']))
            try: await dp.start_polling(bot,allowed_updates=dp.resolve_used_update_types())
            except asyncio.CancelledError: raise
            except Exception as e: log.exception('Child bot failed %s: %s',bid,e)
            finally:
                try: await bot.session.close()
                except Exception: pass
                self.bots.pop(bid,None)
        self.tasks[bid]=asyncio.create_task(run()); return True,'Bot ishga tushirildi.'
    async def stop_child(self,bid:int):
        t=self.tasks.get(int(bid))
        if t and not t.done():
            t.cancel()
            try: await t
            except asyncio.CancelledError: pass
        self.tasks.pop(int(bid),None)
    async def start_many(self,rows):
        for r in rows:
            try: await self.start_child(dict(r))
            except Exception as e: log.exception('start_many error: %s',e)
    async def stop_all(self):
        for bid in list(self.tasks): await self.stop_child(bid)
