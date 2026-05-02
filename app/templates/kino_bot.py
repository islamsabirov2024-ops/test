import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError
from app import database as db
from app.keyboards.kino import (
    user_menu, admin_menu, content_menu, movies_menu, channels_menu_reply,
    settings_menu, premium_menu, payments_menu, ads_menu, text_settings_menu, subscribe_kb, sub_settings_menu
)
from app.services.subscriptions import check_required_subscriptions
from app.utils.text import money

log = logging.getLogger(__name__)

LINK_RE = re.compile(r'(?:https?://)?t\.me/(?:c/(\d+)|([A-Za-z0-9_]+))/(\d+)')


def clean_code(text: str) -> str:
    return (text or '').strip().lower().replace(' ', '')


def parse_tme_link(text: str):
    m = LINK_RE.search(text or '')
    if not m:
        return None
    internal_id, username, msg_id = m.groups()
    if internal_id:
        chat_id = f'-100{internal_id}'
    else:
        chat_id = '@' + username
    return chat_id, int(msg_id)


async def is_admin(bot_id: int, user_id: int) -> bool:
    return await db.is_bot_admin(bot_id, user_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    user = update.effective_user
    await db.add_subscriber(bot_id, user)
    if await is_admin(bot_id, user.id):
        await update.message.reply_html('👑 <b>Admin panel</b>\n\nQuyidagi bo‘limlardan birini tanlang:', reply_markup=admin_menu())
        return
    txt = await db.get_setting(bot_id, 'welcome_text', '👋 Assalomu alaykum {name}!\n\n🎬 Kino kodini yuboring.')
    await update.message.reply_text(txt.replace('{name}', user.first_name or ''), reply_markup=user_menu())


async def send_subscribe_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    channels = await db.list_channels(bot_id)
    await update.message.reply_html('🔐 <b>Kino ko‘rish uchun quyidagi kanallarga obuna bo‘ling:</b>\n\nObuna bo‘lgach <b>✅ Tekshirish</b> tugmasini bosing.', reply_markup=subscribe_kb(channels))


async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    bot_id = context.application.bot_data['bot_id']
    if not await check_required_subscriptions(context.bot, bot_id, update.effective_user.id):
        await send_subscribe_prompt(update, context)
        return
    movie = await db.get_movie(bot_id, clean_code(code))
    if not movie:
        await update.message.reply_text('❌ Bunday kodli kino topilmadi. Kodni tekshirib qayta yuboring.')
        return
    try:
        if movie.get('file_id'):
            await update.message.reply_video(movie['file_id'], caption=movie.get('title') or f"🎬 Kod: {movie['code']}", protect_content=True)
        elif movie.get('source_chat_id') and movie.get('source_message_id'):
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=movie['source_chat_id'],
                message_id=int(movie['source_message_id']),
                protect_content=True,
            )
        else:
            await update.message.reply_text('❌ Kino manbasi topilmadi. Admin qayta yuklashi kerak.')
            return
        await db.inc_movie_views(movie['id'])
    except TelegramError as e:
        log.exception('send movie failed')
        await update.message.reply_text('❌ Kino yuborilmadi. Botni kino kanaliga admin qiling yoki link/file_id ni tekshiring.')


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    s = await db.stats(bot_id)
    await update.message.reply_html(
        '📊 <b>Statistika</b>\n\n'
        f"├ 👥 Foydalanuvchilar: <b>{s['users']}</b> ta\n"
        f"├ 🎬 Kinolar: <b>{s['movies']}</b> ta\n"
        f"├ 🔐 Kanallar: <b>{s['channels']}</b> ta\n"
        f"└ 👁 Ko‘rishlar: <b>{s['views']}</b> ta",
        reply_markup=admin_menu(),
    )


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.application.bot_data['bot_id']
    user = update.effective_user
    t = (update.message.text or '').strip()
    await db.add_subscriber(bot_id, user)
    admin = await is_admin(bot_id, user.id)
    state = context.user_data.get('state')

    if state:
        await handle_state(update, context, state, t)
        return

    if admin:
        if t in ('⏪ Orqaga', '⬅️ Orqaga', 'Asosiy panel'):
            await update.message.reply_text('👑 Kino bot admin paneli', reply_markup=admin_menu()); return
        if t == '📊 Statistika':
            await show_stats(update, context); return
        if t == '🎬 Kontent boshqaruvi':
            await update.message.reply_text('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu()); return
        if t == '🎬 Kinolar':
            await update.message.reply_text('🎬 Kinolar bo‘limidasiz:\n\nQuyidagi amallardan birini tanlang:', reply_markup=movies_menu()); return
        if t == '📥 Kino yuklash':
            context.user_data['state'] = 'movie_code'
            await update.message.reply_text('🔢 Kino kodini yuboring. Masalan: 123 yoki avatar1'); return
        if t == '📝 Kino tahrirlash':
            context.user_data['state'] = 'movie_code'
            await update.message.reply_text('📝 Tahrirlash uchun kino kodini yuboring, keyin yangi video/link yuborasiz:'); return
        if t == '🗑 Kino o‘chirish':
            context.user_data['state'] = 'delete_movie'
            await update.message.reply_text('🗑 O‘chirish uchun kino kodini yuboring:'); return
        if t in ("📋 Kinolar ro'yxati", '📋 Kinolar ro‘yxati'):
            movies = await db.list_movies(bot_id, 30)
            if not movies:
                await update.message.reply_text('📋 Hali kino qo‘shilmagan.', reply_markup=movies_menu()); return
            msg = '📋 Kinolar ro‘yxati:\n\n' + '\n'.join([f"{m['id']}. 🎬 {m['code']} — {m.get('title') or '-'} | 👁 {m.get('views',0)}" for m in movies])
            await update.message.reply_text(msg, reply_markup=movies_menu()); return
        if t == '🔐 Kanallar':
            await update.message.reply_text('🔐 Majburiy obuna kanallari:', reply_markup=channels_menu_reply()); return
        if t == '➕ Kanal qo‘shish':
            context.user_data['state'] = 'channel_add'
            await update.message.reply_text('➕ Kanalni shunday yuboring:\n\nKanal nomi | https://t.me/kanal | @kanal\n\nMasalan: Kino kanal | https://t.me/kinolar040 | @kinolar040'); return
        if t in ("📋 Ro'yxatni ko'rish", '📋 Ro‘yxatni ko‘rish'):
            chs = await db.list_channels(bot_id)
            if not chs:
                await update.message.reply_text('📋 Kanal yo‘q.', reply_markup=channels_menu_reply()); return
            await update.message.reply_text('📋 Kanallar:\n\n' + '\n'.join([f"{c['id']}. {c['title']} — {c['chat_id']}" for c in chs]), reply_markup=channels_menu_reply()); return
        if t == '🗑 Kanalni o‘chirish':
            context.user_data['state'] = 'channel_delete'
            await update.message.reply_text('🗑 O‘chirish uchun kanal ID raqamini yuboring:'); return
        if t == '⚙️ Tizim sozlamalari':
            await update.message.reply_text('⚙️ Tizim sozlamalari bo‘limi:', reply_markup=settings_menu()); return
        if t == '⚙️ Obuna sozlamasi':
            force = await db.get_setting(bot_id, 'force_sub_enabled', '0')
            fake = await db.get_setting(bot_id, 'sub_fake_verify', '0')
            await update.message.reply_text('⚙️ Obuna tekshiruv sozlamasi:', reply_markup=sub_settings_menu(force, fake)); return
        if t == '📣 Reklama':
            enabled = await db.get_setting(bot_id, 'ads_enabled', '0')
            await update.message.reply_text('📣 Reklama sozlamalari:', reply_markup=ads_menu(enabled)); return
        if t == "💳 To'lov tizimlar":
            await update.message.reply_text('💳 To‘lov tizimlari:', reply_markup=payments_menu()); return
        if t == '⚙️ Premium':
            enabled = await db.get_setting(bot_id, 'premium_enabled', '0')
            await update.message.reply_html(f'⚙️ <b>Premium sozlamalar bo‘limidasiz:</b>\n\n🔷 Premium holati: {"✅ Faol" if enabled=="1" else "❌ O‘chiq"}', reply_markup=premium_menu(enabled)); return
        if t == '📝 Matnlar':
            await update.message.reply_text('📝 Matnlarni tanlang:', reply_markup=text_settings_menu()); return
        if t == '👮 Adminlar':
            context.user_data['state'] = 'add_admin'
            admins = await db.list_bot_admins(bot_id)
            await update.message.reply_text('👮 Adminlar:\n' + '\n'.join(str(a['user_id']) for a in admins) + '\n\nYangi admin ID yuboring:'); return
        if t == '📨 Xabar yuborish':
            context.user_data['state'] = 'broadcast'
            await update.message.reply_text('📨 Foydalanuvchilarga yuboriladigan xabarni yozing:'); return
        if t == '👥 Foydalanuvchilar':
            users = await db.list_subscribers(bot_id, 30)
            if not users:
                await update.message.reply_text('👥 Hali foydalanuvchi yo‘q.', reply_markup=admin_menu()); return
            txt = '👥 Foydalanuvchilar ro‘yxati:\n\n' + '\n'.join([f"{i+1}. {u.get('full_name') or '-'} — {u['user_id']}" for i,u in enumerate(users)])
            await update.message.reply_text(txt, reply_markup=admin_menu()); return
        if t == '📥 So‘rovlar':
            await update.message.reply_text('📥 Hozircha yangi so‘rov yo‘q.', reply_markup=admin_menu()); return
        if t == '📮 Postlar':
            await update.message.reply_text('📮 Postlar bo‘limi: reklamalar va postlar Xabar yuborish orqali yuboriladi.', reply_markup=content_menu()); return
        if t == '🔗 Referal':
            bonus = await db.get_setting(bot_id, 'ref_bonus_amount', '200')
            await update.message.reply_text(f'🔗 Referal sozlamasi\n\nHar referal uchun: {bonus} so‘m\n\nYangi bonus summasini yuboring:', reply_markup=content_menu())
            context.user_data['state'] = 'ref_bonus'; return
        if t == '↗️ Ulashish':
            await update.message.reply_text('↗️ Bot ulashish matni:\nhttps://t.me/' + (context.bot.username or ''), reply_markup=settings_menu()); return

    if t in ('🎬 Kino kod yuborish', 'ℹ️ Yordam'):
        await update.message.reply_text('🎬 Kino kodini yozib yuboring. Masalan: 123', reply_markup=user_menu()); return
    if t == '📢 Kanallar':
        chs = await db.list_channels(bot_id)
        if not chs:
            await update.message.reply_text('📢 Hozircha kanal yo‘q.', reply_markup=user_menu()); return
        await update.message.reply_text('📢 Kanallar:', reply_markup=subscribe_kb(chs)); return
    if t == '💎 Premium':
        enabled = await db.get_setting(bot_id, 'premium_enabled', '0')
        if enabled != '1':
            await update.message.reply_text('💎 Premium hozircha o‘chiq.', reply_markup=user_menu()); return
        tariffs = await db.list_premium_tariffs(bot_id)
        if not tariffs:
            await update.message.reply_text(await db.get_setting(bot_id, 'premium_text', '💎 Premium olish uchun admin bilan bog‘laning.'), reply_markup=user_menu()); return
        txt = '💎 Premium tariflar:\n\n' + '\n'.join([f"{x['id']}. {x['name']} — {x['days']} kun — {money(x['price'])}" for x in tariffs])
        await update.message.reply_text(txt, reply_markup=user_menu()); return

    await send_movie(update, context, t)


async def handle_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: str, t: str):
    bot_id = context.application.bot_data['bot_id']
    if state == 'movie_code':
        code = clean_code(t)
        if not code:
            await update.message.reply_text('❌ Kod bo‘sh bo‘lmasin. Qayta yuboring:'); return
        context.user_data['movie_code'] = code
        context.user_data['state'] = 'movie_file'
        await update.message.reply_text('🎥 Endi kino videosini yuboring yoki Telegram post linkini yuboring:\n\nMasalan: https://t.me/kanal/123')
        return
    if state == 'movie_file':
        link = parse_tme_link(t)
        if not link:
            await update.message.reply_text('🎥 Video yuboring yoki to‘g‘ri t.me link yuboring.'); return
        chat, msg = link
        await db.add_movie(bot_id, context.user_data['movie_code'], context.user_data.get('movie_code',''), '', str(chat), int(msg), 0)
        context.user_data.clear()
        await update.message.reply_text('✅ Kino link orqali saqlandi. Serverga video yuklanmadi.', reply_markup=movies_menu())
        return
    if state == 'delete_movie':
        await db.delete_movie(bot_id, clean_code(t))
        context.user_data.clear()
        await update.message.reply_text('🗑 Kino o‘chirildi.', reply_markup=movies_menu())
        return
    if state == 'channel_add':
        parts = [p.strip() for p in t.split('|')]
        title = parts[0] if parts else 'Kanal'
        link = parts[1] if len(parts) > 1 else t
        chat_id = parts[2] if len(parts) > 2 else link.replace('https://t.me/', '@').replace('http://t.me/', '@').replace('t.me/', '@')
        await db.add_channel(bot_id, title, link, chat_id, 1)
        await db.set_setting(bot_id, 'force_sub_enabled', '1')
        context.user_data.clear()
        await update.message.reply_text('✅ Kanal qo‘shildi va majburiy obuna yoqildi.', reply_markup=channels_menu_reply())
        return
    if state == 'channel_delete':
        try:
            await db.delete_channel(bot_id, int(t))
            msg = '🗑 Kanal o‘chirildi.'
        except Exception:
            msg = '❌ ID noto‘g‘ri.'
        context.user_data.clear()
        await update.message.reply_text(msg, reply_markup=channels_menu_reply())
        return
    if state == 'card':
        await db.update_bot_fields(bot_id, card=t)
        context.user_data.clear()
        await update.message.reply_text('✅ Karta saqlandi.', reply_markup=settings_menu())
        return
    if state == 'price':
        price = int(''.join(filter(str.isdigit, t)) or 0)
        await db.update_bot_fields(bot_id, price=price)
        context.user_data.clear()
        await update.message.reply_text('✅ Narx saqlandi.', reply_markup=settings_menu())
        return
    if state == 'broadcast':
        sent, total = await broadcast_text(context.bot, bot_id, t)
        context.user_data.clear()
        await update.message.reply_text(f'✅ Yuborildi: {sent}/{total}', reply_markup=admin_menu())
        return
    if state == 'add_admin':
        try:
            await db.add_bot_admin(bot_id, int(t))
            msg = '✅ Admin qo‘shildi.'
        except Exception:
            msg = '❌ Admin ID noto‘g‘ri.'
        context.user_data.clear()
        await update.message.reply_text(msg, reply_markup=admin_menu())
        return
    if state.startswith('text:'):
        key = state.split(':', 1)[1]
        await db.set_setting(bot_id, key, t)
        context.user_data.clear()
        await update.message.reply_text('✅ Matn saqlandi.', reply_markup=settings_menu())
        return
    if state == 'ads_text':
        await db.set_setting(bot_id, 'ads_text', t)
        context.user_data.clear()
        await update.message.reply_text('✅ Reklama matni saqlandi.', reply_markup=settings_menu())
        return
    if state == 'card_owner':
        await db.update_bot_fields(bot_id, card_owner=t)
        context.user_data.clear()
        await update.message.reply_text('✅ Karta egasi saqlandi.', reply_markup=settings_menu())
        return
    if state == 'premium_mark':
        parts = t.replace('|',' ').split()
        try:
            user_id = int(parts[0]); days = int(parts[1]) if len(parts)>1 else 30
            import time
            await db.set_premium(bot_id, user_id, int(time.time()) + days*86400)
            msg = f'✅ {user_id} ga {days} kun premium berildi.'
        except Exception:
            msg = '❌ Format: user_id kun. Masalan: 5907118746 30'
        context.user_data.clear()
        await update.message.reply_text(msg, reply_markup=admin_menu())
        return
    if state == 'premium_tariff_add':
        try:
            name, days, price = [x.strip() for x in t.split('|')]
            await db.add_premium_tariff(bot_id, name, int(days), int(price))
            msg='✅ Tarif qo‘shildi.'
        except Exception:
            msg='❌ Format: Nomi | kun | narx. Masalan: Start | 7 | 9000'
        context.user_data.clear()
        await update.message.reply_text(msg, reply_markup=admin_menu())
        return
    if state == 'ref_bonus':
        await db.set_setting(bot_id, 'ref_bonus_amount', ''.join(filter(str.isdigit, t)) or '0')
        context.user_data.clear()
        await update.message.reply_text('✅ Referal bonusi saqlandi.', reply_markup=content_menu())
        return


async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'movie_file':
        return
    bot_id = context.application.bot_data['bot_id']
    media = update.message.video or update.message.document
    if not media:
        return
    code = context.user_data.get('movie_code')
    title = update.message.caption or code
    await db.add_movie(bot_id, code, title, media.file_id, '', 0, 0)
    context.user_data.clear()
    await update.message.reply_text('✅ Kino file_id orqali saqlandi. Serverga video yuklanmadi.', reply_markup=movies_menu())


async def broadcast_text(bot, bot_id: int, text: str):
    # Oddiy va xavfsiz broadcast
    import aiosqlite
    from app.database import connect
    sent = 0
    total = 0
    async with connect() as con:
        con.row_factory = aiosqlite.Row
        cur = await con.execute('SELECT user_id FROM subscribers WHERE bot_id=?', (bot_id,))
        rows = await cur.fetchall()
    total = len(rows)
    for r in rows:
        try:
            await bot.send_message(r['user_id'], text)
            sent += 1
        except Exception:
            pass
    return sent, total


async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bot_id = context.application.bot_data['bot_id']
    data = q.data
    if data == 'admin:home':
        await q.message.reply_text('👑 Admin panel', reply_markup=admin_menu()); return
    if data == 'sub:check':
        ok = await check_required_subscriptions(context.bot, bot_id, q.from_user.id)
        await q.message.reply_text('✅ Obuna tasdiqlandi. Endi kino kodini yuboring.' if ok else '❌ Hali obuna bo‘lmagansiz.')
        return
    if data.startswith('set:toggle:'):
        key = data.split(':')[-1]
        old = await db.get_setting(bot_id, key, '0')
        new = '0' if old == '1' else '1'
        await db.set_setting(bot_id, key, new)
        await q.message.reply_text(f"✅ {key}: {'YONDI' if new == '1' else 'O‘CHDI'}")
        return
    if data == 'payset:card':
        context.user_data['state'] = 'card'; await q.message.reply_text('💳 Karta raqamini yozing:'); return
    if data == 'payset:owner':
        context.user_data['state'] = 'card_owner'; await q.message.reply_text('👤 Karta egasini yozing:'); return
    if data == 'payset:price':
        context.user_data['state'] = 'price'; await q.message.reply_text('💰 Oylik narxni yozing:'); return
    if data == 'payset:info':
        b = await db.get_bot(bot_id)
        await q.message.reply_text(f"💳 Karta: {b.get('card') or 'kiritilmagan'}\n💰 Narx: {money(b.get('price') or 0)}")
        return
    if data == 'ads:text':
        context.user_data['state'] = 'ads_text'; await q.message.reply_text('📣 Reklama matnini yozing:'); return
    if data == 'ads:preview':
        await q.message.reply_text(await db.get_setting(bot_id, 'ads_text', 'Reklama matni kiritilmagan.')); return
    if data.startswith('text:'):
        context.user_data['state'] = data; await q.message.reply_text('✍️ Yangi matnni yozing:'); return
    if data == 'premium:mark':
        context.user_data['state'] = 'premium_mark'
        await q.message.reply_text('➕ Premium berish format: user_id kun\nMasalan: 5907118746 30'); return
    if data == 'premium:users':
        users = await db.list_premium_users(bot_id)
        txt = '👥 Premium foydalanuvchilar:\n\n' + ('\n'.join([f"{u['user_id']} — premium_until: {u.get('premium_until')}" for u in users]) or 'Hali premium user yo‘q')
        await q.message.reply_text(txt); return
    if data == 'premium:tariffs':
        trs = await db.list_premium_tariffs(bot_id)
        txt = '📋 Premium tariflar:\n\n' + ('\n'.join([f"{x['id']}. {x['name']} — {x['days']} kun — {money(x['price'])}" for x in trs]) or 'Tarif yo‘q')
        txt += '\n\nYangi tarif qo‘shish uchun format yuboring: Nomi | kun | narx'
        context.user_data['state'] = 'premium_tariff_add'
        await q.message.reply_text(txt); return


def setup_kino_bot(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
