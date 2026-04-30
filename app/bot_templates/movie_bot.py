import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError
from app.services import db
from app.keyboards.movie import subscribe_kb

log = logging.getLogger(__name__)

MOVIE_WAIT = {}

def is_owner(update: Update, bot_row) -> bool:
    u = update.effective_user
    return bool(u and u.id == int(bot_row['owner_id']))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    text = db.get_setting(bot_row['id'], 'welcome_text', '👋 Assalomu alaykum!\n\n🎬 Kino kodini yuboring:')
    if is_owner(update, bot_row):
        text += "\n\n👑 Admin buyruqlar:\n/add - kino qo'shish\n/list - kinolar\n/channels - kanallar\n/settings - sozlamalar"
    await update.effective_message.reply_text(text)

async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row):
        return
    MOVIE_WAIT[update.effective_user.id] = {'step':'code'}
    await update.message.reply_text('➕ Kino qo‘shish\n\n1-qadam: kino kodini yuboring.\nMasalan: 123')

async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row):
        return
    rows = db.list_movies(bot_row['id'])
    if not rows:
        await update.message.reply_text('📭 Hali kino yo‘q.')
        return
    text = '🎬 Kinolar ro‘yxati:\n\n' + '\n'.join([f"#{m['id']} | Kod: {m['code']} | Ko‘rish: {m['views']}" for m in rows[:30]])
    await update.message.reply_text(text)

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row): return
    text = "⚙️ Sozlamalar\n\nMajburiy obuna: /sub_on yoki /sub_off\nPremium: /premium_on yoki /premium_off\nReklama: /ads_on yoki /ads_off\nHiyla tekshirish: /fake_on yoki /fake_off"
    await update.message.reply_text(text)

async def toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row): return
    cmd = update.message.text.strip().lstrip('/')
    mapping = {
        'sub_on':('mandatory_sub','on'), 'sub_off':('mandatory_sub','off'),
        'premium_on':('premium','on'), 'premium_off':('premium','off'),
        'ads_on':('ads','on'), 'ads_off':('ads','off'),
        'fake_on':('fake_verify','on'), 'fake_off':('fake_verify','off'),
    }
    if cmd in mapping:
        db.set_setting(bot_row['id'], mapping[cmd][0], mapping[cmd][1])
        await update.message.reply_text('✅ Sozlama saqlandi.')

async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row): return
    channels = db.list_channels(bot_row['id'])
    text = '🔐 Kanallar\n\nKanal qo‘shish uchun:\n/addchannel Nomi | https://t.me/kanal\n\n'
    text += '\n'.join([f"#{c['id']} {c['title']} - {c['link']}" for c in channels]) or 'Kanal yo‘q.'
    await update.message.reply_text(text)

async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    if not is_owner(update, bot_row): return
    raw = update.message.text.replace('/addchannel','',1).strip()
    if '|' not in raw:
        await update.message.reply_text('❗ Format: /addchannel Kanal nomi | https://t.me/kanal')
        return
    title, link = [x.strip() for x in raw.split('|',1)]
    username = link.rsplit('/',1)[-1] if 't.me/' in link else ''
    db.add_channel(bot_row['id'], title, link, username=username)
    await update.message.reply_text('✅ Kanal qo‘shildi.')

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    bot_row = context.application.bot_data['bot_row']
    if db.get_setting(bot_row['id'], 'mandatory_sub', 'off') != 'on':
        return True
    if db.get_setting(bot_row['id'], 'fake_verify', 'off') == 'on':
        return True
    channels = [c for c in db.list_channels(bot_row['id']) if int(c['checkable']) == 1 and c['username']]
    user_id = update.effective_user.id
    missing = []
    for c in channels:
        chat_id = c['username'] if str(c['username']).startswith('@') else '@' + str(c['username']).lstrip('@')
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                missing.append(c)
        except TelegramError:
            missing.append(c)
    if missing:
        await update.effective_message.reply_text('🔐 Kinoni ko‘rish uchun avval kanallarga obuna bo‘ling:', reply_markup=subscribe_kb(missing))
        return False
    return True

async def check_subs_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ok = await check_subscription(update, context)
    if ok:
        await q.message.reply_text('✅ Obuna tasdiqlandi. Endi kino kodini yuboring.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_row = context.application.bot_data['bot_row']
    uid = update.effective_user.id
    wait = MOVIE_WAIT.get(uid)
    if wait and is_owner(update, bot_row):
        if wait['step'] == 'code':
            wait['code'] = update.message.text.strip()
            wait['step'] = 'media'
            await update.message.reply_text('2-qadam: video/file yuboring yoki kanal postini forward qiling.')
            return
        if wait['step'] == 'media':
            file_id = ''
            if update.message.video: file_id = update.message.video.file_id
            elif update.message.document: file_id = update.message.document.file_id
            elif update.message.animation: file_id = update.message.animation.file_id
            elif update.message.photo: file_id = update.message.photo[-1].file_id
            else:
                await update.message.reply_text('❗ Video, file yoki rasm yuboring.')
                return
            db.add_movie(bot_row['id'], wait['code'], file_id=file_id, title=update.message.caption or '')
            MOVIE_WAIT.pop(uid, None)
            await update.message.reply_text(f"✅ Kino saqlandi. Kod: {wait['code']}")
            return

    if not update.message or not update.message.text:
        return
    code = update.message.text.strip()
    if not await check_subscription(update, context):
        return
    movie = db.get_movie(bot_row['id'], code)
    if not movie:
        await update.message.reply_text('❌ Bunday kod topilmadi. Kodni tekshirib qayta yuboring.')
        return
    db.inc_movie_views(movie['id'])
    caption = movie['title'] or f"🎬 Kino kodi: {movie['code']}"
    if movie['file_id']:
        try:
            await update.message.reply_video(movie['file_id'], caption=caption, protect_content=True)
        except Exception:
            await update.message.reply_document(movie['file_id'], caption=caption, protect_content=True)
    else:
        await update.message.reply_text('❗ Kino fayli topilmadi.')

def build_application(bot_row):
    app = Application.builder().token(bot_row['token']).build()
    app.bot_data['bot_row'] = bot_row
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('add', add_cmd))
    app.add_handler(CommandHandler('list', list_cmd))
    app.add_handler(CommandHandler('settings', settings_cmd))
    app.add_handler(CommandHandler(['sub_on','sub_off','premium_on','premium_off','ads_on','ads_off','fake_on','fake_off'], toggle_cmd))
    app.add_handler(CommandHandler('channels', channels_cmd))
    app.add_handler(CommandHandler('addchannel', add_channel_cmd))
    app.add_handler(CallbackQueryHandler(check_subs_cb, pattern='^child_check_subs$'))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    return app
