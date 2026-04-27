import logging
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import REFERRAL_BONUS_COUNT, REFERRAL_BONUS_DAYS, SUPER_ADMIN_ID, BOT_VERSION
from database import (
    add_or_update_user,
    add_payment,
    add_referral,
    add_referral_reward,
    buy_tariff_with_balance,
    can_buy_tariff_with_balance,
    get_channels,
    get_movie_by_code,
    get_promo_links,
    get_referral_count,
    get_referral_price,
    get_setting,
    get_tariff,
    get_tariffs,
    get_user,
    get_user_balance,
    has_reward_claimed,
    increment_movie_views,
    is_referral_enabled,
    set_user_premium,
)
from keyboards import help_menu_kb, premium_buy_kb, start_user_menu_kb, tariffs_kb

logger = logging.getLogger(__name__)

# Konfiguratsiya muammolari haqida adminni faqat bir marta xabardor qilamiz (process davomida)
_NOTIFIED_BAD_CHANNELS: set[str] = set()


async def _notify_admin_bad_channel(context: ContextTypes.DEFAULT_TYPE, ch_label: str, chat_identifier, error: Exception):
    """Super-adminga noto'g'ri sozlangan kanal haqida bir marta xabar yuboradi."""
    key = f"{ch_label}|{chat_identifier}"
    if key in _NOTIFIED_BAD_CHANNELS:
        return
    _NOTIFIED_BAD_CHANNELS.add(key)
    if not SUPER_ADMIN_ID:
        return
    try:
        await context.bot.send_message(
            chat_id=int(SUPER_ADMIN_ID),
            text=(
                f"⚠️ <b>Majburiy kanal sozlamasida muammo</b>\n\n"
                f"📢 Kanal: <b>{ch_label}</b>\n"
                f"🆔 ID: <code>{chat_identifier}</code>\n"
                f"❌ Xato: <code>{str(error)[:200]}</code>\n\n"
                f"❗ Botni shu kanal/guruhga <b>ADMIN</b> qilib qo'shing yoki admin paneldan kanalni o'chirib tashlang.\n"
                f"Hozircha bu kanal tekshiruvdan o'tkazib yuborilyapti."
            ),
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Super-adminga xabar yuborib bo'lmadi")


def normalize_button_url(url: str | None) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        return f"https://t.me/{raw[1:]}"
    if raw.startswith(("https://", "http://")):
        return raw
    if raw.startswith("t.me/"):
        return f"https://{raw}"
    if " " not in raw and "/" not in raw and "." not in raw:
        return f"https://t.me/{raw}"
    return raw


def _is_user_premium(user: dict | None) -> bool:
    """Botdagi tarif orqali berilgan premiumni tekshiradi. Telegram Premium emas."""
    if not user or int(user.get("is_premium", 0) or 0) != 1:
        return False
    expire = user.get("premium_expire")
    if expire is None:
        return True
    try:
        if isinstance(expire, str):
            expire = datetime.fromisoformat(expire.replace("Z", "+00:00"))
        if expire.tzinfo is None:
            expire = expire.replace(tzinfo=timezone.utc)
        return expire > datetime.now(timezone.utc)
    except Exception:
        return True


async def _movie_requires_premium(movie: dict | None) -> bool:
    # Pullik obuna OFF bo'lsa, premiumga qo'shilgan kinolar ham bepul ochiladi
    if not movie or str(await get_setting("premium_enabled", "1")) != "1":
        return False
    return int(movie.get("is_premium", 0) or 0) == 1


def normalize_chat_identifier(value):
    """Telegram bot.get_chat_member uchun chat ID ni qaytaradi.
    -100... bo'lsa int, @username bo'lsa '@username'. Aks holda None.
    Eslatma: t.me/+xxx (invite link) — Telegram API orqali tekshirib bo'lmaydi."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    # Raqamli ID (-100... yoki musbat)
    if raw.startswith("-100") and raw[1:].isdigit():
        return int(raw)
    if raw.lstrip("-").isdigit():
        return int(raw)
    # @username
    if raw.startswith("@"):
        slug = raw[1:].split("/", 1)[0].strip()
        return f"@{slug}" if slug else None
    # t.me/username (lekin invite-link emas)
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if raw.startswith(prefix):
            slug = raw.replace(prefix, "", 1).strip("/")
            slug = slug.split("/", 1)[0].strip()
            if not slug or slug.startswith("+") or slug.lower() == "c":
                return None
            return f"@{slug}"
    # Faqat so'z (probelsiz, nuqtasiz)
    if " " not in raw and "." not in raw and "/" not in raw:
        return f"@{raw}"
    return None


def extract_chat_identifier(channel: dict):
    """Kanal yozuvidan birinchi ishonchli identifikatorni topadi."""
    for key in ("channel_id", "channel_username", "channel_link"):
        normalized = normalize_chat_identifier(channel.get(key))
        if normalized is not None:
            return normalized
    return None


# Telegram xato matnlari (lowercase)
# 1) foydalanuvchi obuna EMAS holatlari
_NOT_SUBSCRIBED_ERROR_MARKERS = (
    "user not participant",
    "participant_id_invalid",
    "member not found",
    "participant not found",
    "user not found",
    "left the channel",
)
# 2) bot/kanal sozlamasi xatolari
_BOT_CONFIG_ERROR_MARKERS = (
    "member list is inaccessible",
    "chat not found",
    "bot is not a member",
    "not enough rights",
    "forbidden",
    "chat_admin_required",
    "channel_private",
    "chat_admin_invite_required",
    "have no rights",
    "bot was kicked",
)


async def _real_subscription_passed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Foydalanuvchi barcha majburiy kanallarga obuna bo'lganligini tekshiradi.

    Muhim qoidalar:
    - Bot kanal/guruhda admin emas yoki kanal noto'g'ri sozlangan bo'lsa,
      shu kanal o'tkazib yuboriladi (foydalanuvchini cheksiz "obuna bo'l"
      loopiga tushirish o'rniga adminga aniq xabar log'da yoziladi).
    - 'restricted' statusi faqat is_member=True bo'lganda obuna deb hisoblanadi.
    """
    if str(await get_setting("subscription_required", "1")) != "1":
        return True
    # Hiyla rejimi: yoqilgan bo'lsa, foydalanuvchi obuna bo'lmagan bo'lsa ham o'tkazib yuboriladi
    if str(await get_setting("subscription_fake_verify", "0")) == "1":
        logger.info("[obuna] Hiyla rejimi yoqilgan — tekshiruv o'tkazib yuborildi (user=%s)",
                    getattr(update.effective_user, "id", "?"))
        return True
    channels = await get_channels()
    if not channels:
        return True
    user = update.effective_user
    if not user:
        return False

    for ch in channels:
        ch_label = str(ch.get("channel_name") or ch.get("channel_username") or ch.get("channel_id") or "?")
        chat_identifier = extract_chat_identifier(ch)
        if chat_identifier is None:
            raw_link = str(ch.get("channel_link") or "").strip()
            if raw_link and any(x in raw_link.lower() for x in ("instagram.com", "youtube.com", "youtu.be", "tiktok.com", "facebook.com", "x.com", "twitter.com")):
                logger.info("[obuna] '%s' tashqi promo link ekan, tekshiruvdan o'tkazib yuborildi", ch_label)
                continue
            logger.error("[obuna] '%s' uchun yaroqli Telegram identifikatori yo'q", ch_label)
            await _notify_admin_bad_channel(context, ch_label, "invalid", ValueError("Yaroqli Telegram username yoki ID topilmadi"))
            continue
        try:
            member = await context.bot.get_chat_member(chat_id=chat_identifier, user_id=user.id)
            status = str(getattr(member, "status", "")).lower()
            if status in {"creator", "owner", "administrator", "member"}:
                continue
            if status == "restricted" and bool(getattr(member, "is_member", False)):
                continue
            logger.info("[obuna] User %s '%s' kanaliga obuna emas (status=%s)", user.id, ch_label, status)
            return False
        except Exception as e:
            err_text = str(e).lower()
            if any(marker in err_text for marker in _NOT_SUBSCRIBED_ERROR_MARKERS):
                logger.info("[obuna] User %s '%s' kanaliga obuna emas (xato=%s)", user.id, ch_label, e)
                return False
            if any(marker in err_text for marker in _BOT_CONFIG_ERROR_MARKERS):
                logger.error("[obuna] '%s' (%s) ni tekshirib bo'lmadi: %s", ch_label, chat_identifier, e)
                await _notify_admin_bad_channel(context, ch_label, chat_identifier, e)
                return False
            logger.warning("[obuna] Kutilmagan tekshiruv xatosi (%s, %s): %s", ch_label, chat_identifier, e)
            return False
    return True


def clear_user_flow_state(context: ContextTypes.DEFAULT_TYPE):
    for key in (
        "awaiting_payment_screenshot",
        "pending_tariff_id",
        "pending_movie_code",
        "spy_access_granted",
    ):
        context.user_data.pop(key, None)


def build_subscribe_kb(channels: list[dict], promos: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        if extract_chat_identifier(ch) is None:
            continue
        link = ""
        username = str(ch.get("channel_username") or "").strip()
        if username:
            if not username.startswith("@"):
                username = f"@{username}"
            link = normalize_button_url(username)
        if not link:
            channel_link = str(ch.get("channel_link") or "").strip()
            if channel_link.startswith(("https://t.me/", "http://t.me/", "t.me/")) and "/+" not in channel_link and "joinchat" not in channel_link.lower():
                link = normalize_button_url(channel_link)
        if not link:
            channel_id = str(ch.get("channel_id") or "").strip()
            if channel_id.startswith("@"):
                link = normalize_button_url(channel_id)
        if link:
            label = str(ch.get("channel_name") or "").strip() or "Telegram kanal"
            rows.append([InlineKeyboardButton(f"➕ {label}", url=link)])

    for promo in promos:
        title = str(promo.get("title") or "Qo'shimcha link").strip()
        url = str(promo.get("url") or "").strip()
        if url:
            rows.append([InlineKeyboardButton(f"🌐 {title}", url=url)])

    rows.append([InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs")])
    return InlineKeyboardMarkup(rows)


def build_payment_review_kb(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_payment:{payment_id}"), InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_payment:{payment_id}")]])


def balance_buy_kb(tariff_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💰 Balans bilan olish", callback_data=f"buy_tariff_balance:{tariff_id}")],
            [InlineKeyboardButton("💳 Karta orqali olish", callback_data=f"buy_tariff:{tariff_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="buy_menu")],
        ]
    )


async def notify_admin_about_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, payment: dict, tariff: dict):
    if not SUPER_ADMIN_ID:
        return
    user = update.effective_user
    full_name = user.full_name if user else "Noma'lum"
    username = f"@{user.username}" if user and user.username else "yo'q"
    caption = (
        "💳 <b>Yangi premium to'lov cheki</b>\n\n"
        f"👤 Foydalanuvchi: <b>{full_name}</b>\n"
        f"🆔 ID: <code>{user.id if user else 0}</code>\n"
        f"🔗 Username: {username}\n\n"
        f"📦 Tarif: <b>{tariff['name']}</b>\n"
        f"📆 Muddat: <b>{tariff['duration_days']} kun</b>\n"
        f"💰 Narx: <b>{int(tariff['price']):,} so'm</b>\n"
        f"🧾 To'lov ID: <code>{payment['id']}</code>"
    )
    try:
        await context.bot.send_photo(chat_id=SUPER_ADMIN_ID, photo=payment["screenshot_file_id"], caption=caption, parse_mode="HTML", reply_markup=build_payment_review_kb(int(payment["id"])))
    except Exception:
        logger.exception("Admin ga chek yuborishda xato")


async def send_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channels = await get_channels()
    promos = await get_promo_links()
    text = (
        "❌ <b>Kechirasiz, kinoni olish uchun quyidagi kanal/guruhlarga obuna bo'lishingiz kerak.</b>\n\n"
        "✅ Obuna bo'lgach, pastdagi <b>Tekshirish</b> tugmasini bosing."
    )
    reply_markup = build_subscribe_kb(channels, promos)
    if update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)


async def _send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, movie: dict):
    try:
        kind = str(movie.get("source_kind") or "copy")
        protect_content = str(await get_setting("movie_sharing_enabled", "1")) != "1"
        chat_id = update.effective_chat.id
        if kind == "file":
            file_id = str(movie.get("source_file_id") or "")
            file_type = str(movie.get("source_file_type") or "video")
            caption = movie.get("description") or None
            if file_type == "document":
                await context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption, protect_content=protect_content)
            else:
                await context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption, protect_content=protect_content)
        elif kind == "url":
            source_url = str(movie.get("source_url") or "").strip()
            if not source_url:
                raise ValueError("source_url topilmadi")
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("🎬 Ko'rish / Ochish", url=source_url)]])
            text = movie.get("description") or "🎬 Kino tayyor. Pastdagi tugma orqali oching."
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, protect_content=protect_content)
        else:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=movie["source_chat_id"], message_id=movie["source_message_id"], protect_content=protect_content)
        await increment_movie_views(movie["code"])
    except Exception:
        logger.exception("Kino yuborishda xato")
        target = update.callback_query.message if update.callback_query else update.message
        if target:
            await target.reply_text("❌ Xatolik: kino yuborilmadi")


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return
    clear_user_flow_state(context)
    # /start har safar — eski sessiya tozalanadi, yangi kanallar qaytadan tekshiriladi
    context.user_data.pop("spy_access_granted", None)
    name = user.first_name or "Foydalanuvchi"
    referred_by = None
    if context.args:
        try:
            referred_by = int(context.args[0])
            if referred_by == user.id:
                referred_by = None  # o'zini taklif qilolmaydi
        except Exception:
            referred_by = None
    is_new = await add_or_update_user(user.id, user.username, user.full_name or name, referred_by)
    if is_new and referred_by:
        if await add_referral(referred_by, user.id):
            count = await get_referral_count(referred_by)
            if count and count % REFERRAL_BONUS_COUNT == 0 and not await has_reward_claimed(referred_by, count):
                await set_user_premium(referred_by, REFERRAL_BONUS_DAYS)
                await add_referral_reward(referred_by, count, REFERRAL_BONUS_DAYS)
    await update.message.reply_text(f"👋 Assalomu alaykum {name}\n\nKino kodini yuboring 🎬\n\n🆕 Versiya: {BOT_VERSION}", reply_markup=start_user_menu_kb())


async def _show_tariffs_by_message(message, context: ContextTypes.DEFAULT_TYPE, user_id: int | None = None):
    if str(await get_setting("premium_enabled", "1")) != "1":
        await message.reply_text("❌ Pullik obuna hozircha o'chirilgan.")
        return
    tariffs = await get_tariffs()
    if not tariffs:
        await message.reply_text("❌ Hozircha tariflar mavjud emas.")
        return
    target_user_id = int(user_id or message.chat_id)
    balance = await get_user_balance(target_user_id)
    await message.reply_text(
        "💎 <b>Premium obuna</b>\n\n"
        "Premium orqali quyidagilarga ega bo'lasiz:\n"
        "• Premium kinolarni ochish\n• Qo'shimcha qulayliklar\n\n"
        f"💰 <b>Referral balans:</b> {balance:,} so'm\n\n"
        "📋 <b>Quyidagi tariflardan birini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=tariffs_kb(tariffs),
    )


async def _show_tariffs(query, context: ContextTypes.DEFAULT_TYPE):
    await _show_tariffs_by_message(query.message, context, user_id=query.from_user.id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    if data == "check_subs":
        # Har doim haqiqiy obunani tekshirish
        passed = await _real_subscription_passed(update, context)
        if not passed:
            await query.answer("❌ Avval barcha kanallarga obuna bo'ling!", show_alert=True)
            return
        context.user_data["spy_access_granted"] = True
        await query.answer("✅ Obuna tasdiqlandi", show_alert=True)
        pending_code = context.user_data.pop("pending_movie_code", None)
        if pending_code:
            movie = await get_movie_by_code(pending_code)
            if not movie:
                await query.message.reply_text("❌ Kino topilmadi.")
                return
            user = await get_user(query.from_user.id)
            if await _movie_requires_premium(movie) and not _is_user_premium(user):
                await query.message.reply_text("🔒 <b>Ushbu kino pullik</b>\n\n❗️ Ko'rish uchun bot ichidan premium tarif oling.", parse_mode="HTML", reply_markup=premium_buy_kb())
                return
            await query.message.reply_text("✅ Tasdiqlandi\n\n🎬 Kino yuborilmoqda...")
            await _send_movie(update, context, movie)
        else:
            await query.message.reply_text("✅ Tasdiqlandi\n\n🎬 Endi kino kodini yuboring.")
        return
    if data == "buy_menu":
        await query.answer()
        await _show_tariffs(query, context)
        return
    if data.startswith("buy_tariff_balance:"):
        await query.answer()
        try:
            tariff_id = int(data.split(":")[1])
        except (ValueError, IndexError):
            await query.message.reply_text("❌ Noto'g'ri tarif.")
            return
        tariff = await get_tariff(tariff_id)
        if not tariff:
            await query.message.reply_text("❌ Tarif topilmadi.")
            return
        if not await is_referral_enabled():
            await query.message.reply_text("❌ Referral tizimi hozircha o'chirilgan.")
            return
        ok = await can_buy_tariff_with_balance(query.from_user.id, tariff_id)
        if not ok:
            balance = await get_user_balance(query.from_user.id)
            await query.message.reply_text(f"❌ Balans yetarli emas.\n\n💰 Balans: <b>{balance:,} so'm</b>\n📦 Tarif narxi: <b>{int(tariff['price']):,} so'm</b>", parse_mode="HTML")
            return
        result = await buy_tariff_with_balance(query.from_user.id, tariff_id)
        if result:
            await query.message.reply_text(f"✅ <b>Premium muvaffaqiyatli yoqildi</b>\n\n📦 Tarif: <b>{result['tariff_name']}</b>\n📆 Muddat: <b>{result['duration_days']} kun</b>", parse_mode="HTML")
        else:
            await query.message.reply_text("❌ Sotib olib bo'lmadi. Balansingizni tekshiring.")
        return
    if data.startswith("buy_tariff:"):
        await query.answer()
        try:
            tariff_id = int(data.split(":")[1])
        except (ValueError, IndexError):
            await query.message.reply_text("❌ Noto'g'ri tarif.")
            return
        tariff = await get_tariff(tariff_id)
        if not tariff:
            await query.message.reply_text("❌ Tarif topilmadi.")
            return
        if await is_referral_enabled() and await can_buy_tariff_with_balance(query.from_user.id, tariff_id):
            await query.message.reply_text("💡 Sizda bu tarifni referral balans bilan olish imkoniyati bor.\n\nQuyidagidan birini tanlang:", reply_markup=balance_buy_kb(tariff_id))
            return
        context.user_data["pending_tariff_id"] = tariff_id
        context.user_data["awaiting_payment_screenshot"] = True
        payment_card = await get_setting("payment_card", "")
        payment_note = await get_setting("payment_note", "To'lov qilib screenshot yuboring.")
        await query.message.reply_text(f"💎 <b>PREMIUM — To'lov ma'lumotlari</b>\n\n📦 Tarif: <b>{tariff['name']}</b>\n📆 Muddat: <b>{tariff['duration_days']} kun</b>\n💰 Narx: <b>{int(tariff['price']):,} so'm</b>\n💳 Karta: <code>{payment_card}</code>\n\n{payment_note}\n\n❗️ <b>Chekni rasm sifatida yuboring.</b>", parse_mode="HTML")
        return
    if data == "back_start":
        await query.answer()
        await query.message.reply_text("🏠 Bosh menyu", reply_markup=start_user_menu_kb())
        return
    if data == "help_movie_code":
        await query.answer()
        await query.message.reply_text("🎬 Kino olish uchun botga kino kodini yuborasiz.\nMasalan: <code>101</code>", parse_mode="HTML")
        return
    if data == "help_premium":
        await query.answer()
        await query.message.reply_text("💳 Premium orqali premium kinolarni ochasiz.")
        return


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    message = update.message
    text = (message.text or "").strip()
    if message.photo and context.user_data.get("awaiting_payment_screenshot"):
        tariff_id = context.user_data.get("pending_tariff_id")
        tariff = await get_tariff(int(tariff_id)) if tariff_id else None
        if not tariff:
            await message.reply_text("❌ Tarif topilmadi.")
            clear_user_flow_state(context)
            return
        payment = await add_payment(user_id=update.effective_user.id, tariff_id=int(tariff["id"]), amount=int(tariff["price"]), screenshot_file_id=message.photo[-1].file_id, note="User screenshot")
        await notify_admin_about_payment(update, context, payment, tariff)
        clear_user_flow_state(context)
        await message.reply_text("✅ Chek qabul qilindi.\n\nAdmin tekshirganidan keyin premium yoqiladi.", reply_markup=start_user_menu_kb())
        return
    if text == "/start":
        return
    if text in {"🎬 Kino kodini yuborish", "🎬 Kino", "🎥 Kino"}:
        await message.reply_text("🎬 Kino kodini yuboring.")
        return
    if text in {"⭐ Premium obuna", "💳 Premium", "💎 Premium", "💳 Sotib olish", "💳 Obuna tariflari"}:
        await _show_tariffs_by_message(message, context, user_id=update.effective_user.id)
        return
    if text in {"ℹ️ Yordam", "❓ Yordam"}:
        await message.reply_text("ℹ️ Yordam bo'limi", reply_markup=help_menu_kb())
        return
    if text in {"👥 Referral", "👥 Referal"}:
        enabled = await is_referral_enabled()
        if not enabled:
            await message.reply_text("❌ Referral tizimi hozircha o'chirilgan.")
            return
        balance = await get_user_balance(update.effective_user.id)
        count = await get_referral_count(update.effective_user.id)
        price = await get_referral_price()
        bot_username = context.bot.username or "bot"
        await message.reply_text(f"👥 <b>Referral bo'limi</b>\n\n🔗 Sizning havolangiz:\n<code>https://t.me/{bot_username}?start={update.effective_user.id}</code>\n\n👤 Taklif qilgan odamlari: <b>{count}</b>\n💰 Har bir referral uchun: <b>{price:,} so'm</b>\n💳 Balansingiz: <b>{balance:,} so'm</b>", parse_mode="HTML")
        return
    # Qolgan har qanday matn kino kodi sifatida tekshiriladi.
    # Kod faqat raqam emas, harf/raqam aralash ham bo'lishi mumkin.
    movie = await get_movie_by_code(text)
    if not movie:
        await message.reply_text("❌ Bunday kino topilmadi.")
        return

    # 1) Avval majburiy obuna tekshiriladi: user kod yuborganda obuna so'raydi.
    passed = await _real_subscription_passed(update, context)
    if not passed:
        context.user_data["pending_movie_code"] = text
        context.user_data.pop("spy_access_granted", None)
        await send_subscribe(update, context)
        return

    # 2) Keyin pullik kino tekshiriladi. Pullik obuna OFF bo'lsa premium kinolar ham bepul.
    context.user_data["spy_access_granted"] = True
    user = await get_user(update.effective_user.id)
    if await _movie_requires_premium(movie) and not _is_user_premium(user):
        await message.reply_text("🔒 <b>Ushbu kino pullik</b>\n\n❗️ Ko'rish uchun bot ichidan premium tarif oling.", parse_mode="HTML", reply_markup=premium_buy_kb())
        return

    # 3) Hammasi joyida bo'lsa kino yuboriladi.
    await _send_movie(update, context, movie)
    return
