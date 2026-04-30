import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError
from .config import BOT_TOKEN, SUPER_ADMIN_ID, PLATFORM_NAME
from . import db
from .keyboards import main_menu, bot_type_kb, super_panel_kb, super_bot_actions, payment_actions, owner_bot_actions, cleaner_limit_kb
from .texts import WELCOME_USER, SUPER_ADMIN_HELP
from .manager import manager

logging.basicConfig(format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


def is_super(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.add_user(update.effective_user)
    await update.message.reply_text(WELCOME_USER, reply_markup=main_menu(is_super(update.effective_user.id)))

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏠 Bosh menyu", reply_markup=main_menu(is_super(update.effective_user.id)))

async def safe_edit(q, text, markup=None):
    try:
        await q.message.edit_text(text, reply_markup=markup)
    except Exception:
        await q.message.reply_text(text, reply_markup=markup)

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    db.add_user(q.from_user)

    if data == 'home':
        context.user_data.clear()
        await safe_edit(q, "🏠 Bosh menyu", main_menu(is_super(user_id)))
        return

    if data == 'create_bot':
        await safe_edit(q, "🤖 Qaysi turdagi bot yaratmoqchisiz?", bot_type_kb())
        return

    if data in ('type_kino', 'type_cleaner'):
        bot_type = 'kino' if data == 'type_kino' else 'cleaner'
        context.user_data['create_type'] = bot_type
        context.user_data['mode'] = 'await_token'
        name = '🎬 Kino bot' if bot_type == 'kino' else '🧹 Reklama tozalovchi bot'
        await safe_edit(q, f"{name}\n\nBotFatherdan token oling va shu yerga yuboring.\n\nNamuna:\n123456789:ABCDEF...")
        return

    if data == 'my_bots':
        bots = db.list_user_bots(user_id)
        if not bots:
            await safe_edit(q, "📋 Sizda hali bot yo'q.\n\n🤖 Bot yaratish tugmasini bosing.", main_menu(is_super(user_id)))
            return
        rows = []
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        for b in bots:
            icon = '🎬' if b['bot_type'] == 'kino' else '🧹'
            status = {'active':'✅','pending_payment':'💳','stopped':'⏸','blocked':'🚫'}.get(b['status'],'❔')
            rows.append([InlineKeyboardButton(f"{status} {icon} @{b['username'] or 'bot'}", callback_data=f"bot:{b['id']}")])
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="home")])
        await safe_edit(q, "📋 Mening botlarim", InlineKeyboardMarkup(rows))
        return

    if data.startswith('bot:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            await q.answer("⛔ Ruxsat yo'q", show_alert=True)
            return
        txt = (
            f"🤖 Bot ma'lumoti\n\n"
            f"Turi: {'🎬 Kino bot' if b['bot_type']=='kino' else '🧹 Reklama tozalovchi'}\n"
            f"Username: @{b['username'] or 'aniqlanmagan'}\n"
            f"Holat: {b['status']}\n"
            f"Narx: {b['price']} so'm\n"
            f"Karta: {b['card_number'] or 'kiritilmagan'}\n\n"
            f"Botni yoqish/o'chirish faqat Super Admin tomonidan bajariladi."
        )
        await safe_edit(q, txt, owner_bot_actions(bot_id, b['bot_type']))
        return

    if data.startswith('owner_card:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        context.user_data['mode'] = 'await_card'
        context.user_data['bot_id'] = bot_id
        await safe_edit(q, "💳 Karta sozlash\n\nKarta raqami va ismni yuboring.\n\nNamuna:\n8600 1234 5678 9012\nISM FAMILIYA")
        return

    if data.startswith('owner_price:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        context.user_data['mode'] = 'await_price'
        context.user_data['bot_id'] = bot_id
        await safe_edit(q, "💰 Narx sozlash\n\nOyiga qancha so'm bo'lishini yozing.\nMasalan: 30000")
        return

    if data.startswith('send_check:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        context.user_data['mode'] = 'await_check'
        context.user_data['bot_id'] = bot_id
        await safe_edit(q, f"📸 To'lov cheki\n\nKarta: {b['card_number'] or 'karta kiritilmagan'}\nEgasi: {b['card_holder'] or '-'}\nSumma: {b['price']} so'm\n\nChek rasmini yuboring.")
        return

    if data.startswith('owner_cleaner:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        await safe_edit(q, "👥 Guruhga yozish uchun nechta odam qo'shish talab qilinsin?", cleaner_limit_kb(bot_id))
        return

    if data.startswith('climit:'):
        _, bot_id, n = data.split(':')
        bot_id, n = int(bot_id), int(n)
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        db.set_cleaner_add_required(bot_id, n)
        await safe_edit(q, f"✅ Limit saqlandi: {n} odam", owner_bot_actions(bot_id, b['bot_type']))
        return

    if data == 'pay_info':
        await safe_edit(q, "💳 To'lov qilish\n\nAvval bot yarating. Keyin 'Mening botlarim' ichidan botni tanlab, 'Chek yuborish' tugmasini bosing.", main_menu(is_super(user_id)))
        return

    if data == 'help':
        await safe_edit(q, WELCOME_USER, main_menu(is_super(user_id)))
        return

    # SUPER ADMIN ONLY
    if data.startswith('super') or data.startswith('sbot_') or data.startswith('pay_'):
        if not is_super(user_id):
            await q.answer("⛔ Bu panel faqat Super Admin uchun", show_alert=True)
            return

    if data == 'super_panel':
        await safe_edit(q, SUPER_ADMIN_HELP, super_panel_kb())
        return

    if data == 'super_bots':
        bots = db.list_all_bots()
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        rows = []
        for b in bots[:50]:
            icon = '🎬' if b['bot_type']=='kino' else '🧹'
            status = {'active':'✅','pending_payment':'💳','stopped':'⏸','blocked':'🚫'}.get(b['status'],'❔')
            rows.append([InlineKeyboardButton(f"{status} {icon} #{b['id']} @{b['username'] or 'bot'}", callback_data=f"super_bot:{b['id']}")])
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="super_panel")])
        await safe_edit(q, "🤖 Barcha botlar", InlineKeyboardMarkup(rows))
        return

    if data.startswith('super_bot:'):
        bot_id = int(data.split(':')[1])
        b = db.get_bot(bot_id)
        if not b:
            await safe_edit(q, "Bot topilmadi", super_panel_kb())
            return
        txt = (
            f"🤖 Bot #{b['id']}\n\n"
            f"Owner: {b['owner_id']}\n"
            f"Turi: {b['bot_type']}\n"
            f"Username: @{b['username'] or '-'}\n"
            f"Holat: {b['status']}\n"
            f"Narx: {b['price']} so'm\n"
            f"Karta: {b['card_number']}"
        )
        await safe_edit(q, txt, super_bot_actions(bot_id))
        return

    if data.startswith('sbot_on:'):
        bot_id = int(data.split(':')[1])
        db.update_bot_status(bot_id, 'active', 30)
        ok, msg = await manager.start_bot(bot_id)
        await safe_edit(q, f"▶️ {msg}", super_bot_actions(bot_id))
        return

    if data.startswith('sbot_off:'):
        bot_id = int(data.split(':')[1])
        db.update_bot_status(bot_id, 'stopped')
        ok, msg = await manager.stop_bot(bot_id)
        await safe_edit(q, f"⏸ {msg}", super_bot_actions(bot_id))
        return

    if data.startswith('sbot_block:'):
        bot_id = int(data.split(':')[1])
        db.update_bot_status(bot_id, 'blocked')
        await manager.stop_bot(bot_id)
        await safe_edit(q, "🚫 Bot bloklandi", super_bot_actions(bot_id))
        return

    if data == 'super_payments':
        pays = db.list_payments('pending')
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        rows = []
        for p in pays[:50]:
            rows.append([InlineKeyboardButton(f"💳 Chek #{p['id']} | Bot #{p['bot_id']} | {p['amount']} so'm", callback_data=f"payment:{p['id']}:{p['bot_id']}")])
        rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="super_panel")])
        await safe_edit(q, "💳 Kutilayotgan to'lovlar", InlineKeyboardMarkup(rows))
        return

    if data.startswith('payment:'):
        _, pid, bid = data.split(':')
        await safe_edit(q, f"💳 Chek #{pid}\n\nTasdiqlaysizmi?", payment_actions(int(pid), int(bid)))
        return

    if data.startswith('pay_ok:'):
        _, pid, bid = data.split(':')
        pid, bid = int(pid), int(bid)
        db.set_payment_status(pid, 'approved')
        db.update_bot_status(bid, 'active', 30)
        ok, msg = await manager.start_bot(bid)
        b = db.get_bot(bid)
        try:
            await context.bot.send_message(b['owner_id'], f"✅ To'lov tasdiqlandi!\n\n@{b['username']} botingiz ishga tushdi.")
        except Exception:
            pass
        await safe_edit(q, f"✅ Tasdiqlandi. {msg}", super_panel_kb())
        return

    if data.startswith('pay_no:'):
        pid = int(data.split(':')[1])
        db.set_payment_status(pid, 'rejected')
        await safe_edit(q, "❌ To'lov rad etildi", super_panel_kb())
        return

    if data == 'super_stats':
        bots = db.list_all_bots()
        active = sum(1 for b in bots if b['status']=='active')
        await safe_edit(q, f"📊 Statistika\n\nJami botlar: {len(bots)}\nIshlayotgan botlar: {active}", super_panel_kb())
        return

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.add_user(update.effective_user)
    mode = context.user_data.get('mode')

    if mode == 'await_token':
        token = (update.message.text or '').strip()
        bot_type = context.user_data.get('create_type')
        if not TOKEN_RE.match(token):
            await update.message.reply_text("❌ Token noto'g'ri ko'rinadi. BotFather bergan tokenni to'liq yuboring.")
            return
        try:
            temp = Application.builder().token(token).build()
            await temp.initialize()
            me = await temp.bot.get_me()
            await temp.shutdown()
        except Exception as e:
            await update.message.reply_text(f"❌ Token ishlamadi:\n{e}")
            return
        try:
            bot_id = db.create_bot(user_id, bot_type, token, me.username or '', me.first_name or '')
        except Exception as e:
            await update.message.reply_text(f"❌ Bu token oldin qo'shilgan yoki DB xato:\n{e}")
            return
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Bot qo'shildi: @{me.username}\n\n"
            f"Holat: 💳 To'lov kutilmoqda\n"
            f"Endi 'Mening botlarim' bo'limidan kartani sozlang va chek yuboring.",
            reply_markup=main_menu(is_super(user_id))
        )
        try:
            await context.bot.send_message(SUPER_ADMIN_ID, f"🆕 Yangi bot qo'shildi\n\nOwner: {user_id}\nBot: @{me.username}\nTuri: {bot_type}\nID: {bot_id}")
        except Exception:
            pass
        return

    if mode == 'await_card':
        bot_id = context.user_data.get('bot_id')
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        text = update.message.text or ''
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        card = lines[0] if lines else text.strip()
        holder = lines[1] if len(lines) > 1 else ''
        db.update_bot_card(bot_id, card, holder)
        context.user_data.clear()
        await update.message.reply_text("✅ Karta saqlandi", reply_markup=owner_bot_actions(bot_id, b['bot_type']))
        return

    if mode == 'await_price':
        bot_id = context.user_data.get('bot_id')
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        try:
            price = int((update.message.text or '').replace(' ', '').strip())
        except Exception:
            await update.message.reply_text("Faqat raqam yozing. Masalan: 30000")
            return
        db.update_bot_price(bot_id, price)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Narx saqlandi: {price} so'm", reply_markup=owner_bot_actions(bot_id, b['bot_type']))
        return

    if mode == 'await_check':
        bot_id = context.user_data.get('bot_id')
        b = db.get_bot(bot_id)
        if not b or b['owner_id'] != user_id:
            return
        file_id = None
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        if not file_id:
            await update.message.reply_text("📸 Chek rasmi yoki faylini yuboring.")
            return
        pid = db.add_payment(user_id, bot_id, file_id, b['price'])
        context.user_data.clear()
        await update.message.reply_text("✅ Chek qabul qilindi. Super admin tasdiqlashini kuting.", reply_markup=main_menu(is_super(user_id)))
        try:
            await context.bot.send_photo(SUPER_ADMIN_ID, file_id, caption=f"💳 Yangi chek #{pid}\n\nOwner: {user_id}\nBot: #{bot_id} @{b['username']}\nSumma: {b['price']} so'm", reply_markup=payment_actions(pid, bot_id))
        except Exception:
            await context.bot.send_message(SUPER_ADMIN_ID, f"💳 Yangi chek #{pid}\nBot #{bot_id}")
        return

    await update.message.reply_text("Menyudan tanlang 👇", reply_markup=main_menu(is_super(user_id)))

async def post_init(app: Application):
    await manager.start_active_from_db()

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Update error", exc_info=context.error)


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env ichida yo'q")
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('panel', panel))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message))
    app.add_error_handler(error_handler)
    logger.info("%s started", PLATFORM_NAME)
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
