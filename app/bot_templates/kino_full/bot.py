import logging
import time

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from config import BOT_TOKEN, LOG_LEVEL, BOT_VERSION
from database import init_db
from handlers import button_handler, message_handler, start_handler
from admin_handlers import admin_callback_handler, admin_command, admin_message_handler, admin_text_commands

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)
logger = logging.getLogger(__name__)

# Duplicate update tracking
RECENT_UPDATES: dict[int, float] = {}
UPDATE_TTL = 120.0
MAX_RECENT_UPDATES = 5000  # xotira oshib ketmasligi uchun chegara


def is_duplicate_update(update: Update) -> bool:
    update_id = getattr(update, "update_id", None)
    if update_id is None:
        return False
    now = time.time()
    # Eskirganlarni tozalash
    if RECENT_UPDATES:
        expired = [uid for uid, ts in RECENT_UPDATES.items() if now - ts > UPDATE_TTL]
        for uid in expired:
            RECENT_UPDATES.pop(uid, None)
    # Lug'at chegaradan oshib ketsa, eski yarmini tozalash
    if len(RECENT_UPDATES) > MAX_RECENT_UPDATES:
        items = sorted(RECENT_UPDATES.items(), key=lambda x: x[1])
        for uid, _ in items[: len(items) // 2]:
            RECENT_UPDATES.pop(uid, None)
    if update_id in RECENT_UPDATES:
        logger.warning("Duplicate update skipped: %s", update_id)
        return True
    RECENT_UPDATES[update_id] = now
    return False


async def on_startup(app: Application):
    try:
        await init_db()
        logger.info("✅ Database tayyor | version=%s", BOT_VERSION)
    except Exception:
        logger.exception("❌ Database init xatosi")


async def start_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_duplicate_update(update):
        return
    await start_handler(update, context)


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_duplicate_update(update):
        return
    try:
        handled = await admin_callback_handler(update, context)
        if handled:
            return
        await button_handler(update, context)
    except Exception:
        logger.exception("Callback router xatosi")
        # foydalanuvchini bloklab qo'ymaslik uchun qayta o'tkazib yuboramiz
        if update.callback_query:
            try:
                await update.callback_query.answer("❌ Xatolik. Qayta urinib ko'ring.", show_alert=True)
            except Exception:
                pass


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_duplicate_update(update):
        return
    try:
        handled = await admin_text_commands(update, context)
        if handled:
            return
        handled = await admin_message_handler(update, context)
        if handled:
            return
        await message_handler(update, context)
    except Exception:
        logger.exception("Text router xatosi")
        if update.message:
            try:
                await update.message.reply_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
            except Exception:
                pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("❌ Xatolik yuz berdi", exc_info=context.error)
    try:
        if isinstance(update, Update):
            if update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
            elif update.message:
                await update.message.reply_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
    except Exception:
        logger.exception("Error handler ichida ham xato bo'ldi")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .concurrent_updates(False)
        .build()
    )
    app.add_handler(CommandHandler("start", start_router, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("admin", admin_command, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.ALL & ~filters.COMMAND, text_router))
    app.add_error_handler(error_handler)
    logger.info("🚀 Bot ishga tushdi (versiya: %s)", BOT_VERSION)
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES, close_loop=False)


if __name__ == "__main__":
    main()
