import logging
from telegram import Update, Bot
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import TelegramError

from app import database as db
from app.config import SUPER_ADMIN_ID
from app.constants import TEMPLATE_KINO
from app.keyboards.super_admin import (
    super_main,
    user_main,
    owner_main,
    template_choice,
    bot_actions,
    my_bot_actions,
    payment_actions,
    movies_menu,
    channels_menu,
    payment_menu,
    premium_menu,
    ads_menu,
    settings_menu,
    admins_menu,
)
from app.keyboards.common import back
from app.utils.security import is_super_admin
from app.utils.text import short_token, money
from app.services.payments import approve_payment, reject_payment

log = logging.getLogger(__name__)


def clear_state(context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("state", None)
    context.user_data.pop("bot_id", None)
    context.user_data.pop("template", None)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.upsert_user(user)

    if is_super_admin(user.id):
        await update.message.reply_html(
            "👑 <b>Super Admin Panel</b>\n\n"
            "🤖 Platformadagi barcha botlarni boshqarasiz.\n"
            "💳 To‘lovlarni tasdiqlaysiz.\n"
            "▶️ Botlarni ishga tushirasiz yoki to‘xtatasiz.",
            reply_markup=super_main(),
        )
        return

    bots = await db.list_bots(user.id)
    if bots:
        await update.message.reply_html(
            "🛠 <b>Bot Egasi Panel</b>\n\n"
            "Sizda bot mavjud. Quyidagi menyudan botingizni boshqaring.",
            reply_markup=owner_main(),
        )
        return

    await update.message.reply_html(
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "🤖 O‘z botingizni yaratish uchun pastdagi tugmani bosing.\n"
        "💳 Bot yaratish bepul, ishlatish pullik.",
        reply_markup=user_main(),
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()
    await db.upsert_user(user)

    state = context.user_data.get("state")
    bot_id = context.user_data.get("bot_id")

    if state == "await_token":
        await handle_token(update, context, text)
        return

    if state == "await_broadcast" and is_super_admin(user.id):
        await platform_broadcast(update, context, text)
        return

    if state == "await_card" and bot_id:
        await db.update_bot_fields(int(bot_id), card=text)
        clear_state(context)
        await update.message.reply_text("✅ Karta raqami saqlandi.", reply_markup=owner_main())
        return

    if state == "await_card_owner" and bot_id:
        await db.update_bot_fields(int(bot_id), card_owner=text)
        clear_state(context)
        await update.message.reply_text("✅ Karta egasi saqlandi.", reply_markup=owner_main())
        return

    if state == "await_price" and bot_id:
        try:
            price = int(text.replace(" ", ""))
        except ValueError:
            await update.message.reply_text("❌ Narx faqat raqam bo‘lishi kerak. Masalan: 30000")
            return
        await db.update_bot_fields(int(bot_id), price=price)
        clear_state(context)
        await update.message.reply_text(f"✅ Narx saqlandi: {money(price)}", reply_markup=owner_main())
        return

    if state == "await_movie_code" and bot_id:
        context.user_data["movie_code"] = text.lower()
        context.user_data["state"] = "await_movie_file"
        await update.message.reply_text("🎬 Endi kino videosi/faylini yuboring.")
        return

    if state == "await_delete_movie" and bot_id:
        await db.delete_movie(int(bot_id), text.lower())
        clear_state(context)
        await update.message.reply_text("🗑 Kino o‘chirildi.", reply_markup=owner_main())
        return

    if state == "await_channel" and bot_id:
        parts = text.split("|")
        title = parts[0].strip()
        link = parts[1].strip() if len(parts) > 1 else text.strip()
        chat_id = parts[2].strip() if len(parts) > 2 else ""
        await db.add_channel(int(bot_id), title, link, chat_id, 1 if chat_id else 0)
        clear_state(context)
        await update.message.reply_text("✅ Kanal qo‘shildi.", reply_markup=owner_main())
        return

    if state == "await_admin_id" and bot_id:
        try:
            admin_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ Admin ID faqat raqam bo‘lishi kerak.")
            return
        await db.add_bot_admin(int(bot_id), admin_id)
        clear_state(context)
        await update.message.reply_text("✅ Admin qo‘shildi.", reply_markup=owner_main())
        return

    if state == "await_welcome" and bot_id:
        await db.set_setting(int(bot_id), "welcome_text", text)
        clear_state(context)
        await update.message.reply_text("✅ Start matni saqlandi.", reply_markup=owner_main())
        return

    if state == "await_payment_text" and bot_id:
        await db.set_setting(int(bot_id), "payment_text", text)
        clear_state(context)
        await update.message.reply_text("✅ To‘lov matni saqlandi.", reply_markup=owner_main())
        return

    # User menu
    if text == "🤖 Bot yaratish":
        await update.message.reply_text("🤖 Qaysi bot turini yaratmoqchisiz?", reply_markup=template_choice())
        return

    if text == "📋 Mening botlarim":
        await show_my_bots(update, context)
        return

    if text == "💳 To‘lov qilish":
        await show_pay_info(update)
        return

    if text == "ℹ️ Yordam":
        await update.message.reply_text(
            "ℹ️ <b>Yordam</b>\n\n"
            "1️⃣ BotFatherdan yangi bot oching\n"
            "2️⃣ Tokenni bu botga yuboring\n"
            "3️⃣ To‘lov chekini yuboring\n"
            "4️⃣ Admin tasdiqlasa botingiz ishlaydi",
            parse_mode="HTML",
        )
        return

    # Super admin menu
    if is_super_admin(user.id):
        if text == "👑 Super Admin Panel":
            await start(update, context)
            return
        if text == "🤖 Barcha botlar":
            await show_all_bots(update, context)
            return
        if text == "💳 To‘lovlar":
            await show_payments(update, context)
            return
        if text == "📊 Umumiy statistika":
            await show_platform_stats(update)
            return
        if text == "📨 Platforma xabari":
            context.user_data["state"] = "await_broadcast"
            await update.message.reply_text("✍️ Platformaga yuboriladigan xabarni yozing:")
            return
        if text == "⚙️ Platforma sozlamalari":
            await update.message.reply_text("⚙️ Platforma sozlamalari keyingi bosqichda kengaytiriladi.")
            return

    # Owner menu
    bots = await db.list_bots(user.id)
    if bots:
        selected = bots[0]
        context.user_data["bot_id"] = selected["id"]

        if text == "🛠 Bot Egasi Panel":
            await open_owner_panel(update, context, selected["id"])
            return
        if text == "🎬 Kinolar":
            await update.message.reply_text("🎬 Kino boshqaruvi:", reply_markup=movies_menu(selected["id"]))
            return
        if text == "🔐 Majburiy obuna":
            enabled = await db.get_setting(selected["id"], "force_sub_enabled", "0")
            await update.message.reply_text("🔐 Majburiy obuna sozlamalari:", reply_markup=channels_menu(selected["id"], enabled == "1"))
            return
        if text == "💳 Karta va to‘lov":
            await update.message.reply_text("💳 Karta va to‘lov sozlamalari:", reply_markup=payment_menu(selected["id"]))
            return
        if text == "💎 Premium":
            enabled = await db.get_setting(selected["id"], "premium_enabled", "0")
            await update.message.reply_text("💎 Premium sozlamalari:", reply_markup=premium_menu(selected["id"], enabled == "1"))
            return
        if text == "📣 Reklama":
            enabled = await db.get_setting(selected["id"], "ads_enabled", "0")
            await update.message.reply_text("📣 Reklama sozlamalari:", reply_markup=ads_menu(selected["id"], enabled == "1"))
            return
        if text == "📊 Statistika":
            await show_owner_stats(update, selected["id"])
            return
        if text == "👮 Adminlar":
            await update.message.reply_text("👮 Adminlar boshqaruvi:", reply_markup=admins_menu(selected["id"]))
            return
        if text == "⚙️ Sozlamalar":
            await update.message.reply_text("⚙️ Bot sozlamalari:", reply_markup=settings_menu(selected["id"]))
            return

    await update.message.reply_text(
        "👇 Menyudan tanlang.",
        reply_markup=super_main() if is_super_admin(user.id) else (owner_main() if bots else user_main()),
    )


async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
    template = context.user_data.get("template", TEMPLATE_KINO)

    try:
        bot = Bot(token)
        me = await bot.get_me()
    except TelegramError:
        await update.message.reply_text("❌ Token noto‘g‘ri yoki BotFather tokeni emas. Qayta yuboring.")
        return
    except Exception:
        await update.message.reply_text("❌ Token tekshirilmadi. Qayta urinib ko‘ring.")
        return

    try:
        bot_id = await db.create_bot(update.effective_user.id, template, token, me.username or "", me.first_name or "")
    except Exception as e:
        log.exception("create_bot error: %s", e)
        await update.message.reply_text("❌ Bu token oldin qo‘shilgan bo‘lishi mumkin.")
        return

    clear_state(context)

    await update.message.reply_html(
        f"✅ <b>Bot yaratildi!</b>\n\n"
        f"🆔 ID: <code>{bot_id}</code>\n"
        f"🤖 Bot: @{me.username}\n"
        f"📦 Turi: {template}\n"
        f"⏳ Holat: to‘lov kutilmoqda\n\n"
        f"💳 Endi to‘lov chekini rasm qilib yuboring.",
        reply_markup=owner_main(),
    )

    if SUPER_ADMIN_ID:
        try:
            await context.bot.send_message(
                SUPER_ADMIN_ID,
                f"🆕 Yangi bot yaratildi\n\n"
                f"🆔 ID: {bot_id}\n"
                f"👤 Owner: {update.effective_user.id}\n"
                f"📦 Type: {template}\n"
                f"🤖 Bot: @{me.username}",
            )
        except Exception:
            pass


async def show_my_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await db.list_bots(update.effective_user.id)

    if not bots:
        await update.message.reply_text("🤖 Sizda hali bot yo‘q.", reply_markup=user_main())
        return

    for bot in bots:
        await update.message.reply_html(
            f"🤖 <b>@{bot.get('username') or '-'}</b>\n\n"
            f"🆔 ID: <code>{bot['id']}</code>\n"
            f"📦 Turi: {bot['template']}\n"
            f"📌 Holat: <b>{bot['status']}</b>\n"
            f"💳 Narx: {money(bot.get('price') or 0)}\n"
            f"💳 Karta: {bot.get('card') or 'kiritilmagan'}",
            reply_markup=my_bot_actions(bot["id"], bot["status"]),
        )


async def show_all_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bots = await db.list_bots()

    if not bots:
        await update.message.reply_text("🤖 Botlar yo‘q.")
        return

    for bot in bots[:30]:
        await update.message.reply_html(
            f"🤖 <b>@{bot.get('username') or '-'}</b>\n\n"
            f"🆔 ID: <code>{bot['id']}</code>\n"
            f"👤 Owner: <code>{bot['owner_id']}</code>\n"
            f"📦 Turi: {bot['template']}\n"
            f"🔑 Token: <code>{short_token(bot['token'])}</code>\n"
            f"📌 Holat: <b>{bot['status']}</b>",
            reply_markup=bot_actions(bot["id"], bot["status"]),
        )


async def show_pay_info(update: Update):
    bots = await db.list_bots(update.effective_user.id)

    if not bots:
        await update.message.reply_text("❌ Avval bot yarating.", reply_markup=user_main())
        return

    bot = bots[0]
    await update.message.reply_html(
        f"💳 <b>To‘lov ma’lumoti</b>\n\n"
        f"🤖 Bot: @{bot.get('username') or '-'}\n"
        f"💰 Narx: {money(bot.get('price') or 0)}\n"
        f"💳 Karta: <code>{bot.get('card') or 'hali kiritilmagan'}</code>\n"
        f"👤 Karta egasi: {bot.get('card_owner') or '-'}\n\n"
        f"📸 To‘lov qilgach chek rasmini shu botga yuboring.",
    )


async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payments = await db.list_payments("pending")

    if not payments:
        await update.message.reply_text("✅ Kutilayotgan to‘lov yo‘q.")
        return

    for pay in payments:
        await context.bot.send_photo(
            update.effective_chat.id,
            pay["file_id"],
            caption=(
                f"💳 To‘lov #{pay['id']}\n"
                f"🤖 Bot ID: {pay['bot_id']}\n"
                f"👤 User: {pay['user_id']}\n"
                f"📦 {pay.get('template')}"
            ),
            reply_markup=payment_actions(pay["id"]),
        )


async def show_platform_stats(update: Update):
    bots = await db.list_bots()
    active = len([b for b in bots if b["status"] == "active"])
    pending = len([b for b in bots if b["status"] == "pending_payment"])
    blocked = len([b for b in bots if b["status"] == "blocked"])

    await update.message.reply_html(
        "📊 <b>Umumiy statistika</b>\n\n"
        f"🤖 Jami botlar: <b>{len(bots)}</b>\n"
        f"✅ Active: <b>{active}</b>\n"
        f"⏳ To‘lov kutmoqda: <b>{pending}</b>\n"
        f"🚫 Bloklangan: <b>{blocked}</b>"
    )


async def show_owner_stats(update: Update, bot_id: int):
    data = await db.stats(bot_id)
    await update.message.reply_html(
        "📊 <b>Bot statistikasi</b>\n\n"
        f"🎬 Kinolar: <b>{data.get('movies', 0)}</b>\n"
        f"🔐 Kanallar: <b>{data.get('channels', 0)}</b>\n"
        f"👥 Foydalanuvchilar: <b>{data.get('users', 0)}</b>\n"
        f"👁 Ko‘rishlar: <b>{data.get('views', 0)}</b>"
    )


async def platform_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    clear_state(context)
    await update.message.reply_text(
        "📨 Platforma xabari qabul qilindi.\n\n"
        "Keyingi bosqichda barcha ownerlarga yuborish funksiyasi ulanadi.",
        reply_markup=super_main(),
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    bots = await db.list_bots(user.id)

    if not bots:
        await update.message.reply_text("❌ Avval bot yarating.", reply_markup=user_main())
        return

    bot = bots[0]
    file_id = update.message.photo[-1].file_id
    payment_id = await db.add_payment(bot["id"], user.id, file_id, bot.get("price") or 0)

    await update.message.reply_text("✅ Chek qabul qilindi. Super admin tasdiqlashini kuting.")

    if SUPER_ADMIN_ID:
        try:
            await context.bot.send_photo(
                SUPER_ADMIN_ID,
                file_id,
                caption=(
                    f"💳 Yangi chek #{payment_id}\n\n"
                    f"🤖 Bot ID: {bot['id']}\n"
                    f"🤖 Bot: @{bot.get('username') or '-'}\n"
                    f"👤 User: {user.id}\n"
                    f"💰 Summa: {money(bot.get('price') or 0)}"
                ),
                reply_markup=payment_actions(payment_id),
            )
        except Exception:
            pass


async def on_video_or_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    bot_id = context.user_data.get("bot_id")
    code = context.user_data.get("movie_code")

    if state != "await_movie_file" or not bot_id or not code:
        return

    msg = update.message
    file_id = ""

    if msg.video:
        file_id = msg.video.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if not file_id:
        await msg.reply_text("❌ Video yoki fayl topilmadi.")
        return

    title = msg.caption or f"Kino {code}"
    await db.add_movie(int(bot_id), code, title, file_id=file_id)

    clear_state(context)
    await msg.reply_text("✅ Kino saqlandi.", reply_markup=owner_main())


async def open_owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, bot_id: int):
    bot = await db.get_bot(int(bot_id))
    if not bot:
        await update.message.reply_text("❌ Bot topilmadi.")
        return

    context.user_data["bot_id"] = int(bot_id)

    await update.message.reply_html(
        f"🛠 <b>Bot Egasi Panel</b>\n\n"
        f"🤖 Bot: @{bot.get('username') or '-'}\n"
        f"🆔 ID: <code>{bot['id']}</code>\n"
        f"📦 Turi: {bot['template']}\n"
        f"📌 Holat: <b>{bot['status']}</b>\n\n"
        f"Pastdagi menyudan boshqaring.",
        reply_markup=owner_main(),
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    if data == "home":
        await query.message.reply_text(
            "🏠 Bosh menyu",
            reply_markup=super_main() if is_super_admin(user.id) else user_main(),
        )
        return

    if data.startswith("tpl:"):
        template = data.split(":", 1)[1]
        context.user_data["template"] = template
        context.user_data["state"] = "await_token"
        await query.message.reply_text("🔑 BotFatherdan olgan bot tokeningizni yuboring:", reply_markup=back())
        return

    if data.startswith("owner:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        bot = await db.get_bot(bot_id)
        if not bot:
            await query.message.reply_text("❌ Bot topilmadi.")
            return

        if bot["owner_id"] != user.id and not is_super_admin(user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        context.user_data["bot_id"] = bot_id

        if action == "open":
            await query.message.reply_html(
                f"🛠 <b>Bot Egasi Panel</b>\n\n"
                f"🤖 @{bot.get('username') or '-'}\n"
                f"📌 Holat: {bot['status']}",
                reply_markup=owner_main(),
            )
            return

        if action == "info":
            await query.message.reply_html(
                f"ℹ️ <b>Bot ma’lumoti</b>\n\n"
                f"🆔 ID: <code>{bot['id']}</code>\n"
                f"🤖 @{bot.get('username') or '-'}\n"
                f"📦 {bot['template']}\n"
                f"📌 {bot['status']}\n"
                f"💳 {bot.get('card') or '-'}",
            )
            return

        if action == "pay":
            await query.message.reply_text("💳 Chek rasmini shu chatga yuboring.")
            return

    if data.startswith("sbot:"):
        if not is_super_admin(user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        _, status, bot_id = data.split(":")
        bot_id = int(bot_id)

        if status == "info":
            bot = await db.get_bot(bot_id)
            await query.message.reply_html(
                f"ℹ️ <b>Bot #{bot_id}</b>\n\n"
                f"🤖 @{bot.get('username') or '-'}\n"
                f"👤 Owner: <code>{bot.get('owner_id')}</code>\n"
                f"📦 {bot.get('template')}\n"
                f"📌 {bot.get('status')}\n"
                f"💳 {bot.get('card') or '-'}"
            )
            return

        await db.set_bot_status(bot_id, status)
        await query.message.reply_text(f"✅ Bot #{bot_id} holati: {status}")
        return

    if data.startswith("pay:"):
        if not is_super_admin(user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        _, action, payment_id = data.split(":")
        payment_id = int(payment_id)

        if action == "ok":
            ok = await approve_payment(payment_id)
            await query.message.reply_text("✅ To‘lov tasdiqlandi. Bot ishga tushadi." if ok else "❌ To‘lov topilmadi.")
        else:
            await reject_payment(payment_id)
            await query.message.reply_text("❌ To‘lov rad etildi.")
        return

    if data.startswith("movie:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        context.user_data["bot_id"] = bot_id

        if action == "add":
            context.user_data["state"] = "await_movie_code"
            await query.message.reply_text("🎬 Kino kodini yuboring. Masalan: 123")
            return

        if action == "list":
            movies = await db.list_movies(bot_id, 20)
            if not movies:
                await query.message.reply_text("🎬 Kinolar yo‘q.")
                return
            text = "🎬 Kinolar ro‘yxati:\n\n"
            for m in movies:
                text += f"🔹 Kod: {m['code']} | {m.get('title') or '-'} | 👁 {m.get('views', 0)}\n"
            await query.message.reply_text(text)
            return

        if action == "delete":
            context.user_data["state"] = "await_delete_movie"
            await query.message.reply_text("🗑 O‘chiriladigan kino kodini yuboring.")
            return

    if data.startswith("channel:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        if action == "toggle":
            current = await db.get_setting(bot_id, "force_sub_enabled", "0")
            new = "0" if current == "1" else "1"
            await db.set_setting(bot_id, "force_sub_enabled", new)
            await query.message.reply_text(f"🔐 Majburiy obuna: {'✅ Yoqildi' if new == '1' else '❌ O‘chirildi'}")
            return

        if action == "add":
            context.user_data["bot_id"] = bot_id
            context.user_data["state"] = "await_channel"
            await query.message.reply_text(
                "➕ Kanal qo‘shish formati:\n\n"
                "Kanal nomi | https://t.me/kanal | @kanal\n\n"
                "Agar tekshirish shart bo‘lmasa faqat link yuboring."
            )
            return

        if action == "list":
            channels = await db.list_channels(bot_id)
            if not channels:
                await query.message.reply_text("🔐 Kanallar yo‘q.")
                return
            text = "🔐 Kanallar:\n\n"
            for ch in channels:
                text += f"#{ch['id']} — {ch['title']} — {ch['link']}\n"
            await query.message.reply_text(text)
            return

    if data.startswith("card:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        context.user_data["bot_id"] = bot_id

        if action == "set":
            context.user_data["state"] = "await_card"
            await query.message.reply_text("💳 Karta raqamini yuboring:")
            return

        if action == "owner":
            context.user_data["state"] = "await_card_owner"
            await query.message.reply_text("👤 Karta egasining ismini yuboring:")
            return

        if action == "info":
            bot = await db.get_bot(bot_id)
            await query.message.reply_html(
                f"💳 <b>To‘lov ma’lumoti</b>\n\n"
                f"💳 Karta: <code>{bot.get('card') or '-'}</code>\n"
                f"👤 Egasi: {bot.get('card_owner') or '-'}\n"
                f"💰 Narx: {money(bot.get('price') or 0)}"
            )
            return

    if data.startswith("price:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if action == "set":
            context.user_data["bot_id"] = bot_id
            context.user_data["state"] = "await_price"
            await query.message.reply_text("💰 Bot narxini yozing. Masalan: 30000")
            return

    if data.startswith("premium:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        if action == "toggle":
            current = await db.get_setting(bot_id, "premium_enabled", "0")
            new = "0" if current == "1" else "1"
            await db.set_setting(bot_id, "premium_enabled", new)
            await query.message.reply_text(f"💎 Premium: {'✅ Yoqildi' if new == '1' else '❌ O‘chirildi'}")
            return

        await query.message.reply_text("💎 Bu premium bo‘lim keyingi test bosqichida kengaytiriladi.")
        return

    if data.startswith("ads:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        if action == "toggle":
            current = await db.get_setting(bot_id, "ads_enabled", "0")
            new = "0" if current == "1" else "1"
            await db.set_setting(bot_id, "ads_enabled", new)
            await query.message.reply_text(f"📣 Reklama: {'✅ Yoqildi' if new == '1' else '❌ O‘chirildi'}")
            return

        await query.message.reply_text("📣 Reklama bo‘limi keyingi test bosqichida kengaytiriladi.")
        return

    if data.startswith("settings:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        context.user_data["bot_id"] = bot_id

        if action == "welcome":
            context.user_data["state"] = "await_welcome"
            await query.message.reply_text("👋 Yangi start matnini yuboring:")
            return

        if action == "payment_text":
            context.user_data["state"] = "await_payment_text"
            await query.message.reply_text("💳 Yangi to‘lov matnini yuboring:")
            return

        await query.message.reply_text("⚙️ Sozlama saqlandi.")
        return

    if data.startswith("admin:"):
        _, action, bot_id = data.split(":")
        bot_id = int(bot_id)

        if not await can_manage(bot_id, user.id):
            await query.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return

        context.user_data["bot_id"] = bot_id

        if action == "add":
            context.user_data["state"] = "await_admin_id"
            await query.message.reply_text("➕ Admin Telegram ID raqamini yuboring:")
            return

        if action == "list":
            admins = await db.list_bot_admins(bot_id)
            text = "👮 Adminlar:\n\n"
            for a in admins:
                text += f"👤 {a['user_id']} — {a['role']}\n"
            await query.message.reply_text(text)
            return

        await query.message.reply_text("🗑 Admin o‘chirish keyingi test bosqichida ulanadi.")
        return


async def can_manage(bot_id: int, user_id: int) -> bool:
    bot = await db.get_bot(bot_id)
    if not bot:
        return False
    if is_super_admin(user_id):
        return True
    if bot["owner_id"] == user_id:
        return True
    return await db.is_bot_admin(bot_id, user_id)


def setup(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, on_video_or_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
