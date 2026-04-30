import asyncio
import logging
from telegram.ext import Application
from . import db
from .templates.kino_bot import setup_kino_bot
from .templates.cleaner_bot import setup_cleaner_bot

logger = logging.getLogger(__name__)

class ChildBotManager:
    def __init__(self):
        self.apps = {}
        self.tasks = {}

    async def start_active_from_db(self):
        for bot in db.list_all_bots():
            if bot['status'] == 'active':
                await self.start_bot(bot['id'])

    async def start_bot(self, bot_id: int):
        bot = db.get_bot(bot_id)
        if not bot:
            return False, "Bot topilmadi"
        if bot_id in self.apps:
            return True, "Bot allaqachon ishlayapti"
        try:
            app = Application.builder().token(bot['token']).build()
            app.bot_data['bot_id'] = bot_id
            app.bot_data['owner_id'] = bot['owner_id']
            if bot['bot_type'] == 'kino':
                setup_kino_bot(app)
            elif bot['bot_type'] == 'cleaner':
                setup_cleaner_bot(app)
            else:
                return False, "Noma'lum bot turi"

            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True)
            self.apps[bot_id] = app
            logger.info("Child bot started: %s", bot_id)
            return True, "Bot ishga tushdi"
        except Exception as e:
            logger.exception("Child start error")
            return False, f"Xato: {e}"

    async def stop_bot(self, bot_id: int):
        app = self.apps.get(bot_id)
        if not app:
            return True, "Bot hozir ishlamayapti"
        try:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            self.apps.pop(bot_id, None)
            logger.info("Child bot stopped: %s", bot_id)
            return True, "Bot to'xtatildi"
        except Exception as e:
            logger.exception("Child stop error")
            return False, f"Xato: {e}"

manager = ChildBotManager()
