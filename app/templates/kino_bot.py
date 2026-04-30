from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from app import db
from app.keyboards import child_kino_admin_kb

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    owner_id = context.application.bot_data['owner_id']
    if update.effective_user.id == owner_id:
        await update.message.reply_text(
            "🎬 Kino bot admin panel\n\n"
            "Kino qo'shish uchun: avval /add buyrug'ini bosing, keyin KOD va video yuboring.\n"
            "Masalan: kod `123`, keyin video.",
            reply_markup=child_kino_admin_kb()
        )
    else:
        await update.message.reply_text(
            "👋 Assalomu alaykum!\n\n"
            "🎬 Kino ko'rish uchun kino kodini yuboring.\n"
            "Masalan: 123"
        )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.application.bot_data['owner_id']:
        return
    await update.message.reply_text("🎬 Admin panel", reply_markup=child_kino_admin_kb())

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != context.application.bot_data['owner_id']:
        return
    context.user_data['mode'] = 'await_code'
    await update.message.reply_text("➕ Kino qo'shish\n\n1-qadam: kino kodini yuboring.\nMasalan: 123")

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != context.application.bot_data['owner_id']:
        await q.answer("⛔ Ruxsat yo'q", show_alert=True)
        return
    bot_id = context.application.bot_data['bot_id']
    if q.data == 'kino_add':
        context.user_data['mode'] = 'await_code'
        await q.message.edit_text("➕ Kino qo'shish\n\n1-qadam: kino kodini yuboring.")
    elif q.data == 'kino_stats':
        await q.message.edit_text(f"📊 Statistika\n\n🎬 Kinolar soni: {db.movie_count(bot_id)}", reply_markup=child_kino_admin_kb())
    elif q.data == 'kino_card':
        b = db.get_bot(bot_id)
        await q.message.edit_text(f"💳 Karta\n\n{b['card_number']}\n{b['card_holder'] or ''}", reply_markup=child_kino_admin_kb())

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    owner_id = context.application.bot_data['owner_id']
    user_id = update.effective_user.id
    text = (update.message.text or '').strip()

    if user_id == owner_id and context.user_data.get('mode') == 'await_code':
        if not text:
            await update.message.reply_text("Kod matn bo'lishi kerak.")
            return
        context.user_data['new_code'] = text.lower()
        context.user_data['mode'] = 'await_video'
        await update.message.reply_text("2-qadam: endi shu kod uchun video yoki fayl yuboring.")
        return

    if user_id == owner_id and context.user_data.get('mode') == 'await_video':
        code = context.user_data.get('new_code')
        file_id = None
        if update.message.video:
            file_id = update.message.video.file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        elif update.message.animation:
            file_id = update.message.animation.file_id
        if not file_id:
            await update.message.reply_text("Video yoki fayl yuboring.")
            return
        db.add_movie(bot_id, code, file_id, update.message.caption or '')
        context.user_data.clear()
        await update.message.reply_text(f"✅ Kino saqlandi\n\nKod: {code}")
        return

    if text:
        movie = db.get_movie(bot_id, text)
        if not movie:
            await update.message.reply_text("❌ Bunday kod topilmadi. Kodni tekshirib qayta yuboring.")
            return
        await update.message.reply_video(movie['file_id'], caption=movie['caption'] or "🎬 Marhamat")


def setup_kino_bot(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('admin', admin))
    app.add_handler(CommandHandler('add', add_cmd))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message))
