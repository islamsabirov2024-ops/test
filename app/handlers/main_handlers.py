from telegram import Update
from telegram.ext import ContextTypes
from app.config import SUPER_ADMIN_ID
from app.services import db
from app.services.state import set_wait, pop_wait, get_wait
from app.services.telegram_utils import validate_token
from app.keyboards import main as kb
from app.keyboards.movie import movie_admin, movie_content, channels as channels_kb, toggle_menu
from app.keyboards.cleaner import cleaner_admin, invite_limits
from app.services import texts
from app.services.child_manager import toggle_child, start_child

def is_super(user_id:int) -> bool:
    return int(user_id) == int(SUPER_ADMIN_ID)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.add_user(u.id, u.full_name)
    await update.message.reply_text(texts.WELCOME.format(name=u.first_name or 'do‘stim'), reply_markup=kb.user_main(is_super(u.id)))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id
    if data == 'home':
        await q.edit_message_text(texts.WELCOME.format(name=q.from_user.first_name or 'do‘stim'), reply_markup=kb.user_main(is_super(uid)))
    elif data == 'create_menu':
        await q.edit_message_text('🤖 Qanday bot yaratmoqchisiz?\n\nBot yaratish bepul. Ishlatish uchun to‘lov tasdiqlanishi kerak.', reply_markup=kb.create_menu())
    elif data.startswith('create_type:'):
        typ = data.split(':',1)[1]
        set_wait(uid, 'token', typ)
        await q.edit_message_text('🔑 BotFatherdan olingan tokenni yuboring.\n\nMasalan: 123456:ABC-DEF...\n\n❗ Token sir. Uni faqat shu yerga yuboring.')
    elif data == 'my_bots':
        await show_my_bots(q, uid)
    elif data == 'pay_menu':
        await show_my_bots(q, uid, payment=True)
    elif data == 'help':
        await q.edit_message_text('📘 Qo‘llanma\n\n1️⃣ BotFatherdan yangi bot oching\n2️⃣ Tokenni shu yerga yuboring\n3️⃣ Kartaga to‘lov qiling\n4️⃣ Chek yuboring\n5️⃣ Super admin tasdiqlasa bot ishga tushadi', reply_markup=kb.user_main(is_super(uid)))
    elif data == 'super_panel':
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        await q.edit_message_text(texts.SUPER_ADMIN, reply_markup=kb.super_panel())
    elif data == 'admin_bots':
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        await show_admin_bots(q)
    elif data == 'admin_payments':
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        await show_payments(q)
    elif data == 'admin_stats':
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        s = db.stats()
        await q.edit_message_text(f"📊 Statistika\n\n👥 Userlar: {s['users']}\n🤖 Botlar: {s['bots']}\n▶️ Ishlayotgan: {s['active']}\n💳 Pullik: {s['paid']}\n📸 Cheklar: {s['payments']}", reply_markup=kb.super_panel())
    elif data == 'admin_broadcast':
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        await q.edit_message_text('📨 Xabar yuborish bo‘limi tayyor.\n\nKeyingi versiyada barcha userlarga xabar yuborish navbat tizimi bilan ishlaydi.', reply_markup=kb.super_panel())
    elif data.startswith('admin_bot:'):
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        await show_admin_bot(q, int(data.split(':')[1]))
    elif data.startswith('admin_paybot:'):
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        bot_id = int(data.split(':')[1])
        db.set_bot_status(bot_id, status='paid', is_paid=1)
        await q.answer('✅ To‘lov holati ON qilindi')
        await show_admin_bot(q, bot_id)
    elif data.startswith('admin_togglebot:'):
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        bot_id = int(data.split(':')[1])
        ok, msg = await toggle_child(bot_id)
        await q.answer(msg, show_alert=True)
        await show_admin_bot(q, bot_id)
    elif data.startswith('bot_panel:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or (b['owner_id'] != uid and not is_super(uid)): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        if b['bot_type'] == 'movie': await q.edit_message_text('🎬 Kino bot admin paneli\n\n👇 Kerakli bo‘limni tanlang:', reply_markup=movie_admin(bot_id))
        else: await q.edit_message_text('🧹 Reklama tozalovchi admin paneli\n\n👇 Kerakli bo‘limni tanlang:', reply_markup=cleaner_admin(bot_id))
    elif data.startswith('set_card:'):
        bot_id = int(data.split(':')[1]); set_wait(uid, 'card', str(bot_id)); await q.edit_message_text('💳 Karta raqamini yuboring.\nMasalan: 8600 0000 0000 0000')
    elif data.startswith('set_price:'):
        bot_id = int(data.split(':')[1]); set_wait(uid, 'price', str(bot_id)); await q.edit_message_text('💰 Oylik narxni yuboring.\nMasalan: 50000')
    elif data.startswith('send_payment:'):
        bot_id = int(data.split(':')[1]); set_wait(uid, 'payment', str(bot_id)); b=db.get_bot(bot_id); await q.edit_message_text(f"📸 To‘lov chekini rasm qilib yuboring.\n\n💳 Karta: {b['card_number'] or 'hali qo‘yilmagan'}\n💰 Narx: {b['price']} so‘m")
    elif data.startswith('pay_accept:') or data.startswith('pay_reject:'):
        if not is_super(uid): return await q.answer('⛔ Ruxsat yo‘q', show_alert=True)
        pid = int(data.split(':')[1]); p=db.get_payment(pid)
        if not p: return await q.answer('Topilmadi')
        if data.startswith('pay_accept:'):
            db.set_payment_status(pid, 'accepted'); db.set_bot_status(p['bot_id'], status='paid', is_paid=1)
            await q.edit_message_text('✅ Chek tasdiqlandi. Endi botni Super Admin paneldan ishga tushiring.', reply_markup=kb.super_panel())
        else:
            db.set_payment_status(pid, 'rejected'); await q.edit_message_text('❌ Chek rad etildi.', reply_markup=kb.super_panel())
    elif data.startswith('movie_content:'):
        bot_id=int(data.split(':')[1]); await q.edit_message_text('🎬 Kontent boshqaruvi', reply_markup=movie_content(bot_id))
    elif data.startswith('add_movie:'):
        bot_id=int(data.split(':')[1]); set_wait(uid, 'add_movie_code', str(bot_id)); await q.edit_message_text('➕ Kino qo‘shish\n\n1-qadam: kod yuboring. Masalan: 123')
    elif data.startswith('list_movies:'):
        bot_id=int(data.split(':')[1]); rows=db.list_movies(bot_id); text='🎬 Kinolar ro‘yxati\n\n' + ('\n'.join([f"#{m['id']} | {m['code']} | 👁 {m['views']}" for m in rows]) if rows else '📭 Kino yo‘q')
        await q.edit_message_text(text, reply_markup=movie_content(bot_id))
    elif data.startswith('movie_channels:'):
        bot_id=int(data.split(':')[1]); await q.edit_message_text('🔐 Kanallar boshqaruvi', reply_markup=channels_kb(bot_id))
    elif data.startswith('add_channel:'):
        bot_id=int(data.split(':')[1]); set_wait(uid, 'add_channel', str(bot_id)); await q.edit_message_text('➕ Kanal qo‘shish\n\nFormat:\nKanal nomi | https://t.me/kanal')
    elif data.startswith('list_channels:'):
        bot_id=int(data.split(':')[1]); rows=db.list_channels(bot_id); text='🔐 Kanallar\n\n' + ('\n'.join([f"#{c['id']} {c['title']} - {c['link']}" for c in rows]) if rows else '📭 Kanal yo‘q')
        await q.edit_message_text(text, reply_markup=channels_kb(bot_id))
    elif data.startswith(('movie_settings:', 'movie_premium:', 'movie_ads:')):
        bot_id=int(data.split(':')[1]); states={k:db.get_setting(bot_id,k,'off') for k in ['mandatory_sub','fake_verify','premium','ads']}
        await q.edit_message_text('⚙️ Funksiyalarni yoqish/o‘chirish', reply_markup=toggle_menu(bot_id,'movie',states))
    elif data.startswith('toggle:'):
        _, bot_id, key = data.split(':')
        cur = db.get_setting(int(bot_id), key, 'off')
        db.set_setting(int(bot_id), key, 'off' if cur=='on' else 'on')
        states={k:db.get_setting(int(bot_id),k,'off') for k in ['mandatory_sub','fake_verify','premium','ads']}
        await q.edit_message_text('⚙️ Funksiyalarni yoqish/o‘chirish', reply_markup=toggle_menu(int(bot_id),'movie',states))
    elif data.startswith('movie_stats:'):
        bot_id=int(data.split(':')[1]); rows=db.list_movies(bot_id); views=sum([int(m['views']) for m in rows])
        await q.edit_message_text(f'📊 Kino bot statistikasi\n\n🎬 Kinolar: {len(rows)}\n👁 Ko‘rishlar: {views}', reply_markup=movie_admin(bot_id))
    elif data.startswith('movie_payments:'):
        bot_id=int(data.split(':')[1]); b=db.get_bot(bot_id); await q.edit_message_text(f"💳 To‘lov tizimi\n\nKarta: {b['card_number'] or 'yo‘q'}\nNarx: {b['price']} so‘m", reply_markup=kb.bot_owner_actions(bot_id))
    elif data.startswith('cleaner_groups:'):
        bot_id=int(data.split(':')[1]); await q.edit_message_text('👥 Guruhga yozish uchun nechta odam qo‘shish kerak?', reply_markup=invite_limits(bot_id))
    elif data.startswith('cleaner_settings:'):
        bot_id=int(data.split(':')[1]); states={k:db.get_setting(bot_id,k,'on') for k in ['cleaner_links','cleaner_forwards','cleaner_usernames']}
        await q.edit_message_text('⚙️ Tozalash sozlamalari', reply_markup=toggle_menu(bot_id,'cleaner',states))
    elif data.startswith('cleaner_stats:'):
        bot_id=int(data.split(':')[1]); await q.edit_message_text('📊 Reklama tozalovchi statistikasi\n\nGuruh buyruqlari orqali ishlaydi: /status', reply_markup=cleaner_admin(bot_id))

async def show_my_bots(q, uid:int, payment:bool=False):
    bots = db.list_bots(uid)
    if not bots:
        await q.edit_message_text('📭 Sizda hali bot yo‘q.\n\n🤖 Bot yaratish bo‘limidan token yuboring.', reply_markup=kb.user_main(is_super(uid)))
        return
    b = bots[0]
    text = '⚙️ Mening botim\n\n' + '\n'.join([f"#{x['id']} @{x['username']} | {x['bot_type']} | {'▶️' if x['is_running'] else '⏸'} | {'💳 to‘langan' if x['is_paid'] else '🔒 to‘lanmagan'}" for x in bots[:10]])
    await q.edit_message_text(text, reply_markup=kb.bot_owner_actions(b['id']))

async def show_admin_bots(q):
    bots = db.list_bots()
    if not bots:
        await q.edit_message_text('📭 Botlar yo‘q.', reply_markup=kb.super_panel()); return
    rows = []
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    for b in bots[:30]:
        rows.append([InlineKeyboardButton(f"#{b['id']} @{b['username']} | {b['bot_type']} | {'▶️' if b['is_running'] else '⏸'}", callback_data=f"admin_bot:{b['id']}")])
    rows.append([InlineKeyboardButton('⬅️ Orqaga', callback_data='super_panel')])
    await q.edit_message_text('🤖 Barcha botlar', reply_markup=InlineKeyboardMarkup(rows))

async def show_admin_bot(q, bot_id:int):
    b = db.get_bot(bot_id)
    if not b: return await q.edit_message_text('Topilmadi', reply_markup=kb.super_panel())
    text = f"🤖 Bot #{b['id']}\n\nTuri: {b['bot_type']}\nUsername: @{b['username']}\nOwner: {b['owner_id']}\nStatus: {b['status']}\nTo‘lov: {'✅' if b['is_paid'] else '❌'}\nIshlayapti: {'✅' if b['is_running'] else '❌'}"
    await q.edit_message_text(text, reply_markup=kb.admin_bot_actions(b['id'], b['is_running'], b['is_paid']))

async def show_payments(q):
    pays = db.list_pending_payments()
    if not pays:
        await q.edit_message_text('📭 Yangi chek yo‘q.', reply_markup=kb.super_panel()); return
    p = pays[0]
    await q.edit_message_text(f"📸 Chek #{p['id']}\n\nBot: #{p['bot_id']} @{p['username']}\nTuri: {p['bot_type']}\nOwner: {p['owner_id']}", reply_markup=kb.payment_actions(p['id']))

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    st = get_wait(uid)
    if not st:
        await update.message.reply_text('👇 Menyudan tanlang.', reply_markup=kb.user_main(is_super(uid)))
        return
    action = st['action']; data = st['data']
    if action == 'token':
        token = update.message.text.strip()
        try:
            username, title = await validate_token(token)
        except Exception as e:
            await update.message.reply_text('❌ Token noto‘g‘ri yoki BotFather tokeni emas. Qayta yuboring.')
            return
        bot_id = db.create_bot(uid, data, token, username, title)
        pop_wait(uid)
        await update.message.reply_text(f"✅ Bot saqlandi: @{username}\n\n🔒 Hozircha ishlamaydi. Avval to‘lov chekini yuboring, keyin super admin tasdiqlaydi.", reply_markup=kb.bot_owner_actions(bot_id))
    elif action == 'card':
        db.set_bot_card_price(int(data), card=update.message.text.strip()); pop_wait(uid); await update.message.reply_text('✅ Karta saqlandi.', reply_markup=kb.bot_owner_actions(int(data)))
    elif action == 'price':
        db.set_bot_card_price(int(data), price=update.message.text.strip()); pop_wait(uid); await update.message.reply_text('✅ Narx saqlandi.', reply_markup=kb.bot_owner_actions(int(data)))
    elif action == 'payment':
        if not update.message.photo and not update.message.document:
            await update.message.reply_text('❗ Chekni rasm yoki file qilib yuboring.'); return
        file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
        pid = db.add_payment(int(data), uid, file_id); pop_wait(uid)
        await update.message.reply_text('✅ Chek yuborildi. Super admin tekshiradi.')
        try:
            await context.bot.send_photo(SUPER_ADMIN_ID, file_id, caption=f'📸 Yangi chek #{pid}\nBot ID: {data}\nUser: {uid}', reply_markup=kb.payment_actions(pid))
        except Exception:
            pass
    elif action == 'add_movie_code':
        st['code'] = update.message.text.strip(); st['action']='add_movie_media'
        await update.message.reply_text('2-qadam: video/file yuboring.')
    elif action == 'add_movie_media':
        file_id = ''
        if update.message.video: file_id = update.message.video.file_id
        elif update.message.document: file_id = update.message.document.file_id
        elif update.message.photo: file_id = update.message.photo[-1].file_id
        else:
            await update.message.reply_text('❗ Video/file yuboring.'); return
        db.add_movie(int(data), st['code'], file_id=file_id, title=update.message.caption or '')
        pop_wait(uid); await update.message.reply_text(f"✅ Kino qo‘shildi. Kod: {st['code']}", reply_markup=movie_content(int(data)))
    elif action == 'add_channel':
        raw = update.message.text.strip()
        if '|' not in raw:
            await update.message.reply_text('❗ Format: Kanal nomi | https://t.me/kanal'); return
        title, link = [x.strip() for x in raw.split('|',1)]
        username = link.rsplit('/',1)[-1] if 't.me/' in link else ''
        db.add_channel(int(data), title, link, username=username)
        pop_wait(uid); await update.message.reply_text('✅ Kanal qo‘shildi.', reply_markup=channels_kb(int(data)))
