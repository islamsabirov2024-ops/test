import asyncio
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.config import BOT_TOKEN
from app.services.db import init_db
from app.services.health import start_health_server
from app.services.child_manager import start_all_paid
from app.handlers.main_handlers import start, cb, message

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

async def post_init(app: Application):
    asyncio.create_task(start_health_server())
    asyncio.create_task(start_all_paid())

async def main():
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN env kerak')
    init_db()
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(cb))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message))
    log.info('Super MultiBot Public PRO started')
    await application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
