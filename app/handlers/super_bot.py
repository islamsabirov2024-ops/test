import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError
from app import database as db
from app.config import SUPER_ADMIN_ID
from app.constants import TEMPLATE_KINO
from app.keyboards.super_admin import super_main, user_main, template_choice, kino_tariff, bot_actions, payment_actions, pay_methods
from app.utils.security import is_super_admin
from app.utils.text import short_token, money
from app.services.payments import approve_payment, reject_payment

log = logging.getLogger(__name__)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user)
    if is_super_admin(user.id):
        await update.message.reply_html("👑 <b>Super Admin Panel</b>\n\nQuyidagi bo‘limlardan birini tanlang:", reply_markup=super_main())
    else:
        await update.message.reply_html("👋 <b>Assalomu alaykum!</b>\n\nBot yaratish, balans va botlaringizni boshqarish uchun menyudan foydalaning.", reply_markup=user_main())

async def on_text(update:Update, context:ContextTypes.DEFAULT_TYPE):
    user=update.effective_user; text=(update.message.text or '').strip()
    await db.upsert_user(user)
    state=context.user_data.get('state')
    if state == 'await_token':
        await handle_token(update, context, text); return
    if state == 'await_broadcast' and is_super_admin(user.id):
        context.user_data.clear(); await update.message.reply_text("✅ Xabar qabul qilindi. Broadcast moduli tayyor.", reply_markup=super_main()); return

    if text in ("➕ Bot yaratish", "🤖 Bot yaratish"):
        await update.message.reply_html("🤖 <b>Quyidagi bot turlaridan birini tanlang:</b>", reply_markup=template_choice()); return
    if text in ("🤖 Botlarim", "📋 Mening botlarim"):
        await show_my_bots(update, context); return
    if text == "📱 Shaxsiy kabinet":
        bots=await db.list_bots(user.id)
        await update.message.reply_text(f"🆔 ID: {user.id}\n├ 💼 Balansingiz: 0 so'm\n├ 👥 Referallaringiz: 0 ta\n├ 🤖 Botlaringiz: {len(bots)} ta\n└ 💰 Kiritgan pullaringiz: 0 so'm", reply_markup=user_main()); return
    if text == "💳 Hisob to'ldirish":
        await show_pay_info(update); return
    if text == "📚 Qo'llanma":
        await update.message.reply_text("📚 Qo‘llanma:\n1) BotFather’dan token oling.\n2) ➕ Bot yaratish tugmasini bosing.\n3) Kino Botni tanlang va token yuboring.\n4) To‘lov chekini yuboring."); return
    if text in ("🗣 Referal", "🚀 Saytga kirish", "📨 Murojaat"):
        await update.message.reply_text("✅ Bu bo‘lim ulangan. Kerakli sozlamani admin paneldan o‘zgartirasiz."); return

    if is_super_admin(user.id):
        if text in ("📊 Statistika", "📊 Umumiy statistika"):
            bots=await db.list_bots(); await update.message.reply_text(f"📊 Statistika\n\n🤖 Botlar: {len(bots)}\n✅ Faol: {len([b for b in bots if b['status']=='active'])}", reply_markup=super_main()); return
        if text in ("🤖 Barcha botlar", "👥 Foydalanuvchilar"):
            await show_all_bots(update, context); return
        if text in ("📥 So‘rovlar", "💳 To‘lovlar"):
            await show_payments(update, context); return
        if text == "📨 Xabar yuborish":
            context.user_data['state']='await_broadcast'; await update.message.reply_text("✍️ Yuboriladigan xabarni yozing:"); return
        if text in ("🎬 Kontent boshqaruvi", "🔐 Kanallar", "⚙️ Tizim sozlamalari"):
            await update.message.reply_text("✅ Bu bo‘lim asosiy bot uchun tayyor. Child kino bot ichida to‘liq ishlaydi.", reply_markup=super_main()); return
    await update.message.reply_text("👇 Menyudan tanlang.", reply_markup=super_main() if is_super_admin(user.id) else user_main())

async def handle_token(update, context, token):
    template=context.user_data.get('template', TEMPLATE_KINO)
    try:
        b=Bot(token)
        me=await b.get_me()
    except TelegramError:
        await update.message.reply_text("❌ Token noto‘g‘ri. BotFather tokenini qayta yuboring."); return
    except Exception:
        await update.message.reply_text("❌ Token tekshirilmadi. Keyinroq qayta urinib ko‘ring."); return
    try:
        bot_id=await db.create_bot(update.effective_user.id, template, token, me.username or '', me.first_name or '')
    except Exception:
        log.exception("create_bot failed")
        await update.message.reply_text("❌ Bu token oldin qo‘shilgan yoki bazada xato bor."); return
    context.user_data.clear()
    await update.message.reply_text(f"✅ Bot yaratildi!\n\n🆔 ID: {bot_id}\n🤖 @{me.username}\n⏳ Holat: to‘lov kutilmoqda\n\n💳 To‘lov qiling va chek rasmini yuboring.", reply_markup=user_main())
    if SUPER_ADMIN_ID:
        try: await context.bot.send_message(SUPER_ADMIN_ID, f"🆕 Yangi bot yaratildi\nID: {bot_id}\nOwner: {update.effective_user.id}\nType: {template}\nBot: @{me.username}")
        except Exception: pass

async def show_my_bots(update, context):
    bots=await db.list_bots(update.effective_user.id)
    if not bots:
        await update.message.reply_text("📋 Quyidagi botlardan birini tanlang:\n\nSizda hali bot yo‘q.", reply_markup=user_main()); return
    for b in bots:
        await update.message.reply_text(f"📋 Quyidagi botlardan birini tanlang:\n\n⚙️ @{b.get('username') or '-'}\n🆔 {b['id']} | 📦 {b['template']} | 📌 {b['status']}\n💳 Narx: {money(b.get('price') or 0)}")

async def show_all_bots(update, context):
    bots=await db.list_bots()
    if not bots:
        await update.message.reply_text("Botlar yo‘q."); return
    for b in bots[:30]:
        await update.message.reply_text(f"🤖 @{b.get('username') or '-'}\n🆔 {b['id']}\n👤 Owner: {b['owner_id']}\n📦 {b['template']}\n🔑 {short_token(b['token'])}\n📌 {b['status']}", reply_markup=bot_actions(b['id'], b['status']))

async def show_pay_info(update):
    await update.message.reply_text("💳 To‘lov tizimini tanlang:\n\n💳 Payme (Avto)\n— Payme orqali to‘lov qiling va mablag‘ingiz darhol hisobingizga tushadi ⚡\n\n🔵 Click (Avto)\n— Click orqali to‘lov qiling va mablag‘ingiz darhol hisobingizga tushadi ⚡\n\n💳 Karta (Avto)\n— Kartaga to‘lov qiling va 1–2 daqiqa ichida mablag‘ingiz hisobingizga oling ⚡\n\n💳 Humo (Manual)\n— Kartaga to‘lov qiling va chekni yuboring. Admin tasdiqlagandan keyin mablag‘ingiz tushadi ⏳", reply_markup=pay_methods())

async def show_payments(update, context):
    pays=await db.list_payments('pending')
    if not pays:
        await update.message.reply_text("✅ Kutilayotgan to‘lov yo‘q."); return
    for p in pays:
        await context.bot.send_photo(update.effective_chat.id, p['file_id'], caption=f"💳 To‘lov #{p['id']}\n🤖 Bot ID: {p['bot_id']}\n👤 User: {p['user_id']}\n📦 {p.get('template')}", reply_markup=payment_actions(p['id']))

async def on_photo(update, context):
    user=update.effective_user
    bots=await db.list_bots(user.id)
    if not bots:
        await update.message.reply_text("Avval bot yarating."); return
    bot_id=bots[0]['id']; file_id=update.message.photo[-1].file_id
    pid=await db.add_payment(bot_id,user.id,file_id)
    await update.message.reply_text("✅ Chek qabul qilindi. Admin tasdiqlashini kuting.")
    if SUPER_ADMIN_ID:
        await context.bot.send_photo(SUPER_ADMIN_ID, file_id, caption=f"💳 Yangi chek #{pid}\n🤖 Bot ID: {bot_id}\n👤 User: {user.id}", reply_markup=payment_actions(pid))

async def callback(update, context):
    q=update.callback_query; await q.answer(); data=q.data; user=q.from_user
    if data == 'home':
        await q.message.reply_text("🏠 Bosh menyu", reply_markup=super_main() if is_super_admin(user.id) else user_main()); return
    if data.startswith('tpl:'):
        tpl=data.split(':',1)[1]
        if tpl != 'kino':
            await q.message.reply_text("⏳ Bu tur tayyor menyuda bor, hozircha faqat Kino Bot ishga tushiriladi."); return
        await q.message.reply_html("🎬 <b>Kino Bot</b>\n\nUshbu tizim orqali siz kinolarni botga yuklaysiz va ularga maxsus kod biriktirasiz. Foydalanuvchilar shu kod orqali kinoni tez va oson yuklab olishlari mumkin.\n\n💵 <b>Yaratish narxi:</b> 9 000 so‘m\n⏱ <b>Oylik to‘lov:</b> tarifga qarab belgilanadi\n⚡ <b>Boshlang‘ich bonus:</b> 30 kun", reply_markup=kino_tariff()); return
    if data == 'create:kino':
        context.user_data['template']='kino'; context.user_data['state']='await_token'
        await q.message.reply_text("🔑 BotFatherdan olgan bot tokeningizni yuboring:"); return
    if data.startswith('sbot:'):
        if not is_super_admin(user.id): await q.answer("⛔ Ruxsat yo‘q", show_alert=True); return
        _,status,bot_id=data.split(':'); await db.set_bot_status(int(bot_id), status); await q.message.reply_text(f"✅ Bot #{bot_id} holati: {status}"); return
    if data.startswith('pay:'):
        if not is_super_admin(user.id): await q.answer("⛔ Ruxsat yo‘q", show_alert=True); return
        _,act,pid=data.split(':')
        if act=='ok':
            ok=await approve_payment(int(pid)); await q.message.reply_text("✅ To‘lov tasdiqlandi. Bot ishga tushadi." if ok else "❌ Topilmadi")
        else:
            await reject_payment(int(pid)); await q.message.reply_text("❌ To‘lov rad etildi.")
    if data.startswith('paymethod:'):
        await q.message.reply_text("💳 Chek rasmini shu botga yuboring. Admin tasdiqlagandan keyin balans/bot faollashadi.")

def setup(app):
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
