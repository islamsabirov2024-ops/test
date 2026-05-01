from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app import database as db
from app.keyboards.moderator import admin_menu, limit_menu, mute_menu
from app.services.moderation import process_group_message

async def is_admin(update, context):
    return await db.is_bot_admin(context.application.bot_data['bot_id'], update.effective_user.id)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if await is_admin(update, context):
        await update.message.reply_text('🧹 Reklama tozalovchi bot admin panel', reply_markup=admin_menu())
    else:
        await update.message.reply_text('🧹 Men guruhda reklamani tozalayman. Meni guruhga admin qiling.')

async def text(update:Update, context:ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type in ('group','supergroup'):
        await process_group_message(update, context, context.application.bot_data['bot_id']); return
    if not await is_admin(update, context): return
    t=(update.message.text or '').strip()
    if t == '👥 Odam qo‘shish limiti': await update.message.reply_text('👥 Reklama yozish uchun nechta odam qo‘shishi kerak?', reply_markup=limit_menu()); return
    if t == '⏱ Blok vaqti': await update.message.reply_text('⏱ Reklama tashlaganni qancha vaqt bloklaymiz?', reply_markup=mute_menu()); return
    if t == '📊 Statistika': await update.message.reply_text('📊 Moderator statistikasi hozircha invite hisoblari DBda saqlanadi.'); return
    if t == '🧹 Moderator panel': await start(update, context); return

async def cb(update, context):
    q=update.callback_query; await q.answer(); data=q.data; bot_id=context.application.bot_data['bot_id']
    if data.startswith('mod:limit:'):
        n=int(data.split(':')[-1]); await db.update_bot_fields(bot_id, required_invites=n); context.application.bot_data['bot_row']['required_invites']=n; await q.message.reply_text(f'✅ Limit: {n} odam')
    elif data.startswith('mod:mute:'):
        n=int(data.split(':')[-1]); await db.update_bot_fields(bot_id, mute_seconds=n); context.application.bot_data['bot_row']['mute_seconds']=n; await q.message.reply_text(f'✅ Blok vaqti: {n} sekund')
    elif data == 'mod:home': await q.message.reply_text('🧹 Panel', reply_markup=admin_menu())

def setup_moderator_bot(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
