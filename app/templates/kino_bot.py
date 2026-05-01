from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from app import database as db
from app.keyboards.kino import admin_menu, user_menu, content_menu, movies_menu, channels_menu_reply, payments_menu, premium_menu, ads_menu, settings_menu, subscribe_kb
from app.services.subscriptions import check_required_subscriptions
from app.services.broadcast import broadcast_text
from app.services.movies import save_movie, find_movie
from app.utils.text import clean_code, is_menu_text, money
from app.utils.telegram import parse_tme_link

async def is_admin(update, context):
    bot_id=context.application.bot_data['bot_id']
    return await db.is_bot_admin(bot_id, update.effective_user.id)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    bot_id=context.application.bot_data['bot_id']
    await db.add_subscriber(bot_id, update.effective_user)
    if await is_admin(update, context):
        await update.message.reply_html("👑 <b>Kino bot admin panel</b>\n\n👇 Kerakli bo‘limni tanlang:", reply_markup=admin_menu())
    else:
        welcome=await db.get_setting(bot_id,'welcome_text','👋 Assalomu alaykum {name}!\n\n🎬 Kino kodini yuboring.')
        await update.message.reply_text(welcome.replace('{name}', update.effective_user.first_name or ''), reply_markup=user_menu())

async def text(update:Update, context:ContextTypes.DEFAULT_TYPE):
    bot_id=context.application.bot_data['bot_id']; t=(update.message.text or '').strip()
    await db.add_subscriber(bot_id, update.effective_user)
    state=context.user_data.get('state')
    if state:
        await handle_state(update, context, state, t); return

    if await is_admin(update, context):
        if t == '📊 Statistika':
            s=await db.stats(bot_id)
            await update.message.reply_text(f"📊 Statistika\n\n👥 Foydalanuvchilar: {s['users']} ta\n🎬 Kinolar: {s['movies']} ta\n🔐 Kanallar: {s['channels']} ta\n👁 Ko‘rishlar: {s['views']} ta"); return
        if t == '🎬 Kontent boshqaruvi': await update.message.reply_text('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu()); return
        if t == '🎬 Kinolar': await update.message.reply_text('🎬 Kinolar bo‘limidasiz:\n\nQuyidagi amallardan birini tanlang:', reply_markup=movies_menu()); return
        if t == '⏪ Asosiy panel': await update.message.reply_text('👑 Admin panel', reply_markup=admin_menu()); return
        if t == '⬅️ Orqaga': await update.message.reply_text('🎬 Kontent bo‘limi', reply_markup=content_menu()); return
        if t == '📥 Kino yuklash': context.user_data['state']='movie_code'; await update.message.reply_text('🔢 Kino kodini yuboring:'); return
        if t == '📋 Kinolar ro‘yxati':
            movies=await db.list_movies(bot_id,30)
            txt='🎬 Kinolar ro‘yxati:\n\n'+'\n'.join([f"{m['id']}. {m['code']} — {m.get('title') or '-'} 👁 {m['views']}" for m in movies]) if movies else 'Kinolar yo‘q.'
            await update.message.reply_text(txt); return
        if t == '🗑 Kino o‘chirish': context.user_data['state']='delete_movie'; await update.message.reply_text('🗑 O‘chirish uchun kino kodini yuboring:'); return
        if t == '📝 Kino tahrirlash': await update.message.reply_text('✍️ Shu kodga yangi video/link yuborsangiz, eski kino ustiga yoziladi.'); return
        if t == '🔐 Kanallar': await show_channels_menu(update, context); return
        if t == '➕ Kanal qo‘shish': context.user_data['state']='channel_add'; await update.message.reply_text('➕ Kanal yuboring:\nFormat: Nomi | https://t.me/kanal | @kanal'); return
        if t == '📋 Ro‘yxatni ko‘rish':
            chs=await db.list_channels(bot_id)
            await update.message.reply_text('🔐 Majburiy obuna kanallari:\n\n'+'\n'.join([f"{c['id']}. {c['title']} — {c['chat_id']}" for c in chs]) if chs else 'Kanal yo‘q.'); return
        if t == '🗑 Kanalni o‘chirish': context.user_data['state']='channel_delete'; await update.message.reply_text('🗑 Kanal ID yuboring:'); return
        if t == '💳 To‘lov tizimlari' or t == "💳 To'lov tizimlar": await update.message.reply_text('💳 To‘lov sozlamalari', reply_markup=payments_menu()); return
        if t == '💎 Premium' or t == '⚙️ Premium': await update.message.reply_text('⚙️ Premium sozlamalari bo‘limidasiz:', reply_markup=premium_menu(await db.get_setting(bot_id,'premium_enabled','0'))); return
        if t == '📣 Reklama': await update.message.reply_text('📣 Reklama sozlamalari', reply_markup=ads_menu(await db.get_setting(bot_id,'ads_enabled','0'))); return
        if t == '📨 Xabar yuborish': context.user_data['state']='broadcast'; await update.message.reply_text('✍️ Barcha foydalanuvchilarga yuboriladigan xabarni yozing:'); return
        if t == '👮 Adminlar': context.user_data['state']='add_admin'; await update.message.reply_text('➕ Admin qilish uchun Telegram ID yuboring:'); return
        if t == '⚙️ Tizim sozlamalari': await update.message.reply_text('⚙️ Tizim sozlamalari bo‘limi:', reply_markup=settings_menu()); return
        if t == '📝 Matnlar': context.user_data['state']='text:welcome_text'; await update.message.reply_text('✍️ Start matnini yozing. {name} ishlatishingiz mumkin:'); return
        if t in ('👥 Foydalanuvchilar','📥 So‘rovlar','📮 Postlar','🔗 Referal','↗️ Ulashish'):
            await update.message.reply_text('✅ Bo‘lim tayyor. Keyingi bosqichda kengaytiriladi.'); return

    if is_menu_text(t):
        await update.message.reply_text('👇 Menyudan foydalaning.'); return
    ok=await check_required_subscriptions(context.bot, bot_id, update.effective_user.id)
    if not ok:
        channels=await db.list_channels(bot_id)
        await update.message.reply_text('🔐 Kino ko‘rish uchun avval kanallarga obuna bo‘ling:', reply_markup=subscribe_kb(channels)); return
    movie=await find_movie(bot_id, t)
    if not movie:
        await update.message.reply_text('❌ Bunday kod topilmadi.'); return
    await db.inc_movie_views(movie['id'])
    if movie.get('file_id'):
        await update.message.reply_video(movie['file_id'], caption=f"🎬 {movie.get('title') or movie['code']}", protect_content=True)
    elif movie.get('source_chat_id') and movie.get('source_message_id'):
        await context.bot.copy_message(update.effective_chat.id, movie['source_chat_id'], movie['source_message_id'], protect_content=True)
    else:
        await update.message.reply_text('❌ Kino fayli topilmadi.')

async def handle_state(update, context, state, t):
    bot_id=context.application.bot_data['bot_id']
    if state == 'movie_code':
        context.user_data['movie_code']=clean_code(t); context.user_data['state']='movie_file'; await update.message.reply_text('🎥 Endi video yuboring yoki t.me link yuboring:'); return
    if state == 'movie_file':
        link=parse_tme_link(t)
        if link:
            chat,msg=link; await save_movie(bot_id, context.user_data['movie_code'], context.user_data.get('movie_title',''), '', str(chat), msg)
            context.user_data.clear(); await update.message.reply_text('✅ Kino link orqali saqlandi.', reply_markup=movies_menu()); return
        await update.message.reply_text('🎥 Video yuboring yoki to‘g‘ri link yuboring.'); return
    if state == 'delete_movie':
        await db.delete_movie(bot_id, clean_code(t)); context.user_data.clear(); await update.message.reply_text('🗑 Kino o‘chirildi.', reply_markup=movies_menu()); return
    if state == 'channel_add':
        parts=t.split('|')
        title=parts[0].strip() if parts else 'Kanal'; link=parts[1].strip() if len(parts)>1 else t.strip(); chat_id=parts[2].strip() if len(parts)>2 else link.replace('https://t.me/','@').replace('http://t.me/','@').replace('t.me/','@')
        await db.add_channel(bot_id,title,link,chat_id,1); context.user_data.clear(); await update.message.reply_text('✅ Kanal qo‘shildi.', reply_markup=channels_menu_reply()); return
    if state == 'channel_delete':
        try: await db.delete_channel(bot_id,int(t))
        except Exception: pass
        context.user_data.clear(); await update.message.reply_text('🗑 Kanal o‘chirildi.', reply_markup=channels_menu_reply()); return
    if state == 'card':
        await db.update_bot_fields(bot_id, card=t); context.user_data.clear(); await update.message.reply_text('✅ Karta saqlandi.'); return
    if state == 'price':
        await db.update_bot_fields(bot_id, price=int(''.join(filter(str.isdigit,t)) or 0)); context.user_data.clear(); await update.message.reply_text('✅ Narx saqlandi.'); return
    if state == 'broadcast':
        sent,total=await broadcast_text(context.bot,bot_id,t); context.user_data.clear(); await update.message.reply_text(f'✅ Yuborildi: {sent}/{total}'); return
    if state == 'add_admin':
        await db.add_bot_admin(bot_id,int(t)); context.user_data.clear(); await update.message.reply_text('✅ Admin qo‘shildi.'); return
    if state.startswith('text:'):
        key=state.split(':',1)[1]
        await db.set_setting(bot_id,key,t); context.user_data.clear(); await update.message.reply_text('✅ Matn saqlandi.'); return
    if state == 'ads_text':
        await db.set_setting(bot_id,'ads_text',t); context.user_data.clear(); await update.message.reply_text('✅ Reklama matni saqlandi.'); return
    if state == 'premium_mark':
        movie=await db.get_movie(bot_id, clean_code(t))
        if movie: await save_movie(bot_id, movie['code'], movie['title'], movie['file_id'], movie['source_chat_id'], movie['source_message_id'], 1)
        context.user_data.clear(); await update.message.reply_text('✅ Premium belgilandi.'); return

async def video(update, context):
    if context.user_data.get('state') != 'movie_file': return
    bot_id=context.application.bot_data['bot_id']
    vid=update.message.video or update.message.document
    await save_movie(bot_id, context.user_data['movie_code'], update.message.caption or context.user_data['movie_code'], vid.file_id, '', 0)
    context.user_data.clear(); await update.message.reply_text('✅ Kino video orqali saqlandi.', reply_markup=movies_menu())

async def show_channels_menu(update, context):
    await update.message.reply_text('🔐 Majburiy obuna kanallari:', reply_markup=channels_menu_reply())

async def cb(update, context):
    q=update.callback_query; await q.answer(); data=q.data; bot_id=context.application.bot_data['bot_id']
    if data == 'admin:home': await q.message.reply_text('👑 Admin panel', reply_markup=admin_menu()); return
    if data.startswith('set:toggle:'):
        key=data.split(':')[-1]; old=await db.get_setting(bot_id,key,'0'); new='0' if old=='1' else '1'; await db.set_setting(bot_id,key,new); await q.message.reply_text(f"✅ {key}: {'YONDI' if new=='1' else 'O‘CHDI'}"); return
    if data == 'payset:card': context.user_data['state']='card'; await q.message.reply_text('💳 Karta raqamini yozing:'); return
    if data == 'payset:price': context.user_data['state']='price'; await q.message.reply_text('💰 Oylik narxni yozing:'); return
    if data == 'payset:info':
        b=context.application.bot_data['bot_row']; await q.message.reply_text(f"💳 Karta: {b.get('card') or 'kiritilmagan'}\n💰 Narx: {money(b.get('price') or 0)}"); return
    if data == 'premium:mark': context.user_data['state']='premium_mark'; await q.message.reply_text('💎 Premium qilish uchun kino kodini yuboring:'); return
    if data == 'premium:users': await q.message.reply_text('👥 Premium foydalanuvchilar ro‘yxati keyingi bosqichda kengaytiriladi.'); return
    if data == 'premium:tariffs': await q.message.reply_text('📋 Premium tariflar keyingi bosqichda kengaytiriladi.'); return
    if data == 'ads:text': context.user_data['state']='ads_text'; await q.message.reply_text('📣 Reklama matnini yozing:'); return
    if data.startswith('text:'): context.user_data['state']=data; await q.message.reply_text('✍️ Yangi matnni yozing:'); return
    if data == 'sub:check':
        ok=await check_required_subscriptions(context.bot, bot_id, q.from_user.id); await q.message.reply_text('✅ Obuna tasdiqlandi. Kino kodini yuboring.' if ok else '❌ Hali obuna bo‘lmagansiz.'); return


def setup_kino_bot(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
