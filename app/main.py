import asyncio
import logging
from telegram.ext import Application
from app.config import BOT_TOKEN, LOG_LEVEL
from app.database import init_db
from app.handlers.super_bot import setup as setup_super_bot
from app.services.children import sync_loop

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', level=getattr(logging, LOG_LEVEL.upper(), logging.INFO))
log=logging.getLogger(__name__)

async def post_init(app):
    asyncio.create_task(sync_loop())

def main():
    if not BOT_TOKEN:
        raise RuntimeError('BOT_TOKEN .env ichida yo‘q')
    asyncio.run(init_db())
    app=Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    setup_super_bot(app)
    log.info('Super MultiBot All-in-One started')
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
