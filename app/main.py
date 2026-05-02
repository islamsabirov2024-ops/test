import asyncio
import logging

from telegram.ext import Application

from app.config import BOT_TOKEN, LOG_LEVEL
from app.database import init_db
from app.handlers.super_bot import setup as setup_super_bot
from app.services.children import sync_loop, shutdown_all_children

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, str(LOG_LEVEL).upper(), logging.INFO),
)
log = logging.getLogger(__name__)

_child_task: asyncio.Task | None = None


async def start_app() -> None:
    """
    Python 3.11 / Railway / Render uchun ENG ISHONCHLI polling usuli.
    Bu yerda app.run_polling() ishlatilmaydi, chunki ayrim hostinglarda
    `There is no current event loop in thread MainThread` xatosini beradi.
    """
    global _child_task

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env ichida yo'q")

    await init_db()

    app = Application.builder().token(BOT_TOKEN).build()
    setup_super_bot(app)

    await app.initialize()
    await app.start()

    if not app.updater:
        raise RuntimeError("Updater topilmadi. Polling ishlashi uchun updater kerak.")

    await app.updater.start_polling(drop_pending_updates=True)
    _child_task = asyncio.create_task(sync_loop(), name="child-bot-sync-loop")

    log.info("Super MultiBot All-in-One started")

    try:
        # Botni doimiy ishlatib turadi
        while True:
            await asyncio.sleep(3600)
    finally:
        log.info("Super MultiBot shutting down...")
        if _child_task:
            _child_task.cancel()
            try:
                await _child_task
            except asyncio.CancelledError:
                pass

        await shutdown_all_children()

        if app.updater and app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main() -> None:
    asyncio.run(start_app())


if __name__ == "__main__":
    main()
