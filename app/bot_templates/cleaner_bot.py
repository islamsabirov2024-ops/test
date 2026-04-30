import re
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from app.services import db

LINK_RE = re.compile(r'(https?://|t\.me/|telegram\.me/|www\.|@\w{4,})', re.I)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if update.effective_chat.type == 'private':
        text = "🧹 Reklama tozalovchi bot\n\nGuruhga admin qilib qo‘shing.\n\nAdmin buyruqlar:\n/settings - sozlamalar\n/limit 5 - yozish uchun nechta odam qo‘shish kerak\n/status - guruh holati"
        await update.message.reply_text(text)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('⚙️ Sozlamalar\n\n/limit 5, /limit 10, /limit 15, /limit 20, /limit 25, /limit 30\n\nReklama tashlagan user 30 sekund yozolmaydi.')

async def limit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if update.effective_chat.type not in ('group','supergroup'):
        await update.message.reply_text('Bu buyruq guruhda ishlaydi.')
        return
    try:
        n = int(context.args[0])
    except Exception:
        n = 5
    if n not in (5,10,15,20,25,30): n = 5
    chat = update.effective_chat
    db.set_cleaner_group(bot_row['id'], str(chat.id), chat.title or '', required_invites=n)
    db.set_group_invites(bot_row['id'], str(chat.id), n)
    await update.message.reply_text(f'✅ Limit saqlandi: yozish uchun {n} odam qo‘shish kerak.')

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    chat = update.effective_chat
    g = db.get_cleaner_group(bot_row['id'], str(chat.id))
    if not g:
        db.set_cleaner_group(bot_row['id'], str(chat.id), chat.title or '')
        g = db.get_cleaner_group(bot_row['id'], str(chat.id))
    await update.message.reply_text(f"🧹 Guruh himoyasi faol\n\n👥 Kerakli odam: {g['required_invites']}\n🚫 Blok vaqti: {g['mute_seconds']} sekund")

async def handle_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    msg = update.message
    if not msg or not msg.new_chat_members: return
    inviter = msg.from_user
    for _ in msg.new_chat_members:
        db.add_invite(bot_row['id'], str(msg.chat_id), inviter.id, 1)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    msg = update.message
    if not msg or msg.chat.type not in ('group','supergroup'): return
    db.set_cleaner_group(bot_row['id'], str(msg.chat_id), msg.chat.title or '')
    g = db.get_cleaner_group(bot_row['id'], str(msg.chat_id))
    required = int(g['required_invites']) if g else 5
    user_count = db.get_invites(bot_row['id'], str(msg.chat_id), msg.from_user.id)
    text = msg.text or msg.caption or ''
    bad = False
    if LINK_RE.search(text): bad = True
    if msg.forward_origin or msg.forward_from_chat: bad = True
    if bad and user_count < required:
        try:
            await msg.delete()
        except Exception:
            pass
        try:
            await context.bot.restrict_chat_member(
                chat_id=msg.chat_id,
                user_id=msg.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=int(msg.date.timestamp()) + int(g['mute_seconds'] if g else 30)
            )
        except Exception:
            pass
        try:
            await context.bot.send_message(msg.chat_id, f"🚫 {msg.from_user.mention_html()} reklama tashladi.\n\n✍️ Yozish uchun avval {required} odam qo‘shishi kerak.\n⏳ 30 sekund bloklandi.", parse_mode='HTML')
        except Exception:
            pass

def build_application(bot_row):
    app = Application.builder().token(bot_row['token']).build()
    app.bot_data['bot_row'] = bot_row
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('settings', settings))
    app.add_handler(CommandHandler('limit', limit_cmd))
    app.add_handler(CommandHandler('status', status_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_members))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    return app
