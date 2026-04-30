from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters
from app import db
import re

URL_RE = re.compile(r"(https?://|t\.me/|@\w+|www\.)", re.I)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧹 Reklama tozalovchi bot\n\n"
        "Meni guruhga admin qiling. Reklama linklarni o'chiraman.\n"
        "Agar odam qo'shish talabi yoqilgan bo'lsa, foydalanuvchi belgilangan miqdorda odam qo'shmaguncha yozolmaydi."
    )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    owner_id = context.application.bot_data['owner_id']
    if update.effective_user.id != owner_id:
        return
    s = db.get_cleaner_settings(bot_id)
    await update.message.reply_text(
        f"⚙️ Cleaner sozlamalari\n\n"
        f"👥 Talab: {s['add_required'] if s else 5} odam qo'shish\n"
        f"🚫 Reklama uchun blok: {s['mute_seconds'] if s else 30} sekund\n\n"
        f"Limitni glavni bot ichidan o'zgartirasiz."
    )

async def clean_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return
    if update.effective_chat.type not in ('group', 'supergroup'):
        return
    text = update.message.text or update.message.caption or ''
    if URL_RE.search(text):
        try:
            await update.message.delete()
        except Exception:
            pass
        try:
            until = update.message.date.timestamp() + 30
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=update.effective_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(until)
            )
        except Exception:
            pass
        try:
            warn = await context.bot.send_message(update.effective_chat.id, "🚫 Reklama mumkin emas. 30 sekund bloklandi.")
        except Exception:
            return

async def new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Bu joy keyingi versiyada aniq user qo'shish hisoblagichi bilan kengaytiriladi.
    return


def setup_cleaner_bot(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('settings', settings))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_members))
    app.add_handler(MessageHandler(filters.TEXT | filters.CaptionRegex(r'.+'), clean_message))
