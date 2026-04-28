from __future__ import annotations

from html import escape
import logging
import re
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import BOT_USERNAME
import database as db
from keyboards import (
    admin_add_movie_source_choose_kb,
    admin_admins_menu_kb,
    admin_channel_actions_kb,
    admin_channel_public_methods_kb,
    admin_channel_type_kb,
    admin_channels_menu_kb,
    admin_manage_done_kb,
    admin_menu_reply_kb,
    admin_movie_edit_kb,
    admin_movie_saved_kb,
    admin_movie_type_kb,
    admin_movies_menu_kb,
    admin_premium_actions_kb,
    admin_promo_actions_kb,
    admin_promos_menu_kb,
    admin_referral_price_kb,
    admin_referral_settings_kb,
    admin_tariff_saved_kb,
    admin_tariff_vip_kb,
    admin_tariffs_menu_kb,
    back_menu,
    broadcast_confirm_kb,
    payment_review_kb,
    start_user_menu_kb,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# STATE CONSTANTS
# ------------------------------------------------------------------
STATE_NONE = ""

STATE_ADD_MOVIE_CODE = "admin_add_movie_code"
STATE_ADD_MOVIE_SOURCE = "admin_add_movie_source"
STATE_DELETE_MOVIE_CODE = "admin_delete_movie_code"
STATE_EDIT_MOVIE_FIND = "admin_edit_movie_find"
STATE_EDIT_MOVIE_CODE = "admin_edit_movie_code"
STATE_EDIT_MOVIE_NAME = "admin_edit_movie_name"
STATE_EDIT_MOVIE_CAPTION = "admin_edit_movie_caption"

STATE_ADD_CHANNEL_ID = "admin_add_channel_id"
STATE_ADD_CHANNEL_NAME = "admin_add_channel_name"
STATE_DELETE_CHANNEL_ID = "admin_delete_channel_id"

STATE_ADD_PROMO_TITLE = "admin_add_promo_title"
STATE_ADD_PROMO_URL = "admin_add_promo_url"
STATE_DELETE_PROMO_ID = "admin_delete_promo_id"

STATE_ADD_TARIFF_NAME = "admin_add_tariff_name"
STATE_ADD_TARIFF_PRICE = "admin_add_tariff_price"
STATE_ADD_TARIFF_DURATION = "admin_add_tariff_duration"
STATE_ADD_TARIFF_VIP = "admin_add_tariff_vip"
STATE_DELETE_TARIFF_ID = "admin_delete_tariff_id"

STATE_ADD_ADMIN_ID = "admin_add_admin_id"
STATE_DELETE_ADMIN_ID = "admin_delete_admin_id"

STATE_SET_CARD = "admin_set_card"
STATE_SET_NOTE = "admin_set_note"
STATE_SET_REFERRAL_PRICE = "admin_set_referral_price"

# Broadcast states (yetishmay turgan edi)
STATE_BROADCAST_KIND = "admin_broadcast_kind"
STATE_BROADCAST_TEXT = "admin_broadcast_text"
STATE_BROADCAST_FORWARD = "admin_broadcast_forward"
STATE_BROADCAST_BUTTONS = "admin_broadcast_buttons"

STATE_WAIT_PAYMENT_REJECT_REASON = "admin_wait_payment_reject_reason"
STATE_REVOKE_PREMIUM_USER_ID = "admin_revoke_premium_user_id"
STATE_REVOKE_PREMIUM_REASON = "admin_revoke_premium_reason"


# ------------------------------------------------------------------
# LOKAL KEYBOARDLAR (keyboards.py da yo'q edi — shu yerda tuzildi)
# ------------------------------------------------------------------
def _broadcast_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Oddiy xabar", callback_data="broadcast_type_text")],
        [InlineKeyboardButton("📨 Forward xabar", callback_data="broadcast_type_forward")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_open")],
    ])


def _broadcast_ready_kb(include_button: bool = True, user_buttons=None) -> InlineKeyboardMarkup:
    """Preview tagidagi keyboard: avval foydalanuvchi qo‘shgan reklama
    tugmalari (har biri alohida qator), pastida boshqaruv tugmalari."""
    rows: list[list[InlineKeyboardButton]] = []
    if user_buttons:
        for row in user_buttons:
            rows.append(list(row))
    if include_button:
        rows.append([InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="broadcast_add_button")])
    rows.append([InlineKeyboardButton("📨 Yuborish", callback_data="broadcast_send")])
    rows.append([InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_open")])
    return InlineKeyboardMarkup(rows)


# ------------------------------------------------------------------
# STATE HELPERS
# ------------------------------------------------------------------
def _clear_admin_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "admin_state",
        "new_movie_code",
        "new_movie_source_chat_id",
        "new_movie_source_message_id",
        "new_movie_source_kind",
        "new_movie_file_id",
        "new_movie_file_type",
        "new_movie_source_url",
        "new_movie_is_premium",
        "new_channel_id",
        "new_channel_name",
        "new_channel_username",
        "new_channel_link",
        "new_promo_title",
        "new_promo_url",
        "new_tariff_name",
        "new_tariff_price",
        "new_tariff_duration",
        "new_tariff_is_vip",
        "broadcast_kind",
        "broadcast_text",
        "broadcast_buttons_text",
        "broadcast_buttons",
        "broadcast_source_chat_id",
        "broadcast_source_message_id",
        "reject_payment_id",
        "revoke_premium_user_id",
        "edit_movie_code_target",
    ):
        context.user_data.pop(key, None)


def _set_state(context: ContextTypes.DEFAULT_TYPE, state: str) -> None:
    context.user_data["admin_state"] = state


def _get_state(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("admin_state", STATE_NONE)


def _extract_text(update: Update) -> str:
    if update.message and update.message.text:
        return update.message.text.strip()
    return ""


def _normalize_movie_code(value: str) -> str:
    return str(value or "").strip().lower()


def _parse_money(value: str) -> int:
    return int(str(value).replace(" ", "").replace(",", ""))


def _format_money(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return str(value)


def _format_dt(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def _format_remaining_text(seconds: Any) -> str:
    try:
        seconds = int(float(seconds or 0))
    except Exception:
        return "-"
    if seconds <= 0:
        return "Tugagan"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    if days > 0:
        return f"{days} kun {hours} soat"
    minutes = (seconds % 3600) // 60
    return f"{hours} soat {minutes} daqiqa"


def _parse_int(text: str, field_name: str = "qiymat") -> int:
    value = str(text or "").strip()
    if not re.fullmatch(r"-?\d+", value):
        raise ValueError(f"{field_name} butun son bo‘lishi kerak.")
    return int(value)


def extract_forward_source_info(msg) -> tuple[Optional[str], Optional[int]]:
    forward_chat = getattr(msg, "forward_from_chat", None)
    forward_message_id = getattr(msg, "forward_from_message_id", None)
    if forward_chat and forward_message_id:
        return str(forward_chat.id), int(forward_message_id)

    origin = getattr(msg, "forward_origin", None)
    if origin:
        message_id = getattr(origin, "message_id", None)
        chat = getattr(origin, "chat", None)
        if chat and message_id:
            return str(chat.id), int(message_id)
        sender_chat = getattr(origin, "sender_chat", None)
        if sender_chat and message_id:
            return str(sender_chat.id), int(message_id)

    return None, None


def extract_message_link_info(text: str) -> tuple[Optional[str], Optional[int]]:
    text = (text or "").strip()

    m1 = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]{4,})/(\d+)", text)
    if m1:
        return f"@{m1.group(1)}", int(m1.group(2))

    m2 = re.search(r"(?:https?://)?t\.me/c/(\d+)/(\d+)", text)
    if m2:
        return str(int(f"-100{m2.group(1)}")), int(m2.group(2))

    return None, None


def _parse_buttons(text: str) -> list[list[InlineKeyboardButton]]:
    """[Matn|Link] formatidagi tugmalarni parse qiladi."""
    buttons: list[list[InlineKeyboardButton]] = []
    for match in re.finditer(r"\[([^|\]]+)\|([^\]]+)\]", text or ""):
        label = match.group(1).strip()
        url = match.group(2).strip()
        if not label or not url:
            continue
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("t.me/")):
            raise ValueError(f"Link http, https yoki t.me bilan boshlanishi kerak: {url}")
        if url.startswith("t.me/"):
            url = "https://" + url
        buttons.append([InlineKeyboardButton(label, url=url)])
    if not buttons:
        raise ValueError("Hech qanday to‘g‘ri tugma topilmadi.")
    return buttons


async def _reply(update: Update, text: str, **kwargs):
    if update.message:
        return await update.message.reply_text(text, **kwargs)
    if update.callback_query and update.callback_query.message:
        return await update.callback_query.message.reply_text(text, **kwargs)
    return None


# ------------------------------------------------------------------
# USER NOTIFICATIONS
# ------------------------------------------------------------------
async def _notify_user_payment_approved(
    context: ContextTypes.DEFAULT_TYPE,
    payment: dict[str, Any],
) -> None:
    user_id = int(payment["user_id"])
    tariff_name = escape(str(payment.get("tariff_name") or "Obuna"))
    duration_days = int(payment.get("duration_days") or 0)
    amount_text = _format_money(payment.get("amount", 0))
    approved_time = _format_dt(payment.get("reviewed_at"))

    text = (
        "✅ <b>To‘lov tasdiqlandi!</b>\n\n"
        f"📦 <b>Tarif:</b> {tariff_name}\n"
        f"📆 <b>Muddat:</b> {duration_days} kun\n"
        f"👤 <b>Foydalanuvchi:</b> <code>{user_id}</code>\n"
        f"💰 <b>To‘lov summasi:</b> {amount_text} so‘m\n"
        f"⏰ <b>Sana:</b> {approved_time}"
    )
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        logger.exception("Approved payment user notification failed: %s", user_id)


async def _notify_user_payment_rejected(
    context: ContextTypes.DEFAULT_TYPE,
    payment: dict[str, Any],
    reason: str = "",
) -> None:
    user_id = int(payment["user_id"])
    text = "❌ <b>To‘lov tasdiqlanmadi</b>\n\nIltimos, to‘lovni qayta tekshirib, to‘g‘ri screenshot yuboring."
    if reason and reason != "-":
        text += f"\n\n📝 Sabab: <b>{escape(reason)}</b>"
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        logger.exception("Rejected payment user notification failed: %s", user_id)


async def _notify_user_premium_revoked(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    reason: str = "",
) -> None:
    text = "⚠️ <b>Obunangiz olib qo‘yildi</b>"
    if reason:
        text += f"\n\n📝 Sabab: <b>{escape(reason)}</b>"
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception:
        logger.exception("Premium revoke user notification failed: %s", user_id)


# ------------------------------------------------------------------
# MENU SHOWS
# ------------------------------------------------------------------
async def _show_admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _clear_admin_state(context)
    await _reply(
        update,
        "🔐 <b>Admin panel</b>\n\nKerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_menu_reply_kb(),
    )


async def _show_movies_menu(update: Update) -> None:
    await _reply(
        update,
        "🎬 <b>Kinolar bo‘limi</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_movies_menu_kb(),
    )


async def _show_channels_menu(update: Update) -> None:
    await _reply(
        update,
        "📢 <b>Kanallar bo‘limi</b>\n\n"
        "Majburiy obuna va reklama linklar shu yerda boshqariladi.\n\n"
        "📣 <b>Majburiy obuna</b> — Telegram kanal yoki guruh qo‘shish\n"
        "🌐 <b>Reklama linklar</b> — Instagram, YouTube, TikTok, sayt linklari\n\n"
        "Kerakli bo‘limni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_channels_menu_kb(),
    )


async def _show_promos_menu(update: Update) -> None:
    await _reply(
        update,
        "🌐 <b>Reklama linklar bo‘limi</b>\n\n"
        "Bu yerga oddiy linklar qo‘shiladi.\n"
        "Masalan:\n"
        "• Instagram\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Sayt havolalari\n\n"
        "⚠️ Bu linklar tekshirilmaydi, faqat foydalanuvchiga ko‘rsatiladi.",
        parse_mode="HTML",
        reply_markup=admin_promos_menu_kb(),
    )


async def _show_tariffs_menu(update: Update) -> None:
    await _reply(
        update,
        "💳 <b>Tariflar bo‘limi</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_tariffs_menu_kb(),
    )


async def _show_admins_menu(update: Update) -> None:
    await _reply(
        update,
        "👮 <b>Adminlar bo‘limi</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=admin_admins_menu_kb(),
    )


async def _show_referral_settings(update: Update) -> None:
    referral_enabled = await db.get_setting("referral_enabled", "1")
    referral_price = await db.get_setting("referral_price", "300")

    text = (
        "👥 <b>Referral tizimi sozlamalari</b>\n\n"
        f"• Referral tizimi: {'✅ Yoqilgan' if str(referral_enabled) == '1' else '❌ O‘chirilgan'}\n"
        f"• Referral summasi: <b>{_format_money(referral_price)} so‘m</b>\n\n"
        "⚠️ <b>Muhim:</b>\n"
        "• Referral balans alohida\n"
        "• Haqiqiy pul alohida\n"
        "• Ikkalasi bir-biriga qo‘shilmaydi\n"
        "• Tarifni faqat to‘liq referral balans bilan yoki to‘liq karta bilan olish mumkin"
    )
    await _reply(
        update,
        text,
        parse_mode="HTML",
        reply_markup=admin_referral_settings_kb(),
    )


async def _show_settings_menu(update: Update) -> None:
    subscription_required = await db.get_setting("subscription_required", "1")
    premium_enabled = await db.get_setting("premium_enabled", "1")
    subscription_fake_verify = await db.get_setting("subscription_fake_verify", "1")
    payment_card = await db.get_setting("payment_card", "")
    payment_note = await db.get_setting("payment_note", "")
    movie_sharing_enabled = await db.get_setting("movie_sharing_enabled", "1")

    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"• Majburiy obuna: {'✅ Yoqilgan' if str(subscription_required) == '1' else '❌ O‘chirilgan'}\n"
        f"• Hiyla tasdiqlash: {'✅ Yoqilgan' if str(subscription_fake_verify) == '1' else '❌ O‘chirilgan'}\n"
        f"• Pullik obuna: {'✅ Yoqilgan' if str(premium_enabled) == '1' else '❌ O‘chirilgan'}\n"
        f"• Kino ulashish: {'✅ Yoqilgan' if str(movie_sharing_enabled) == '1' else '❌ O‘chirilgan'}\n"
        f"• Karta: <code>{escape(payment_card or 'Kiritilmagan')}</code>\n"
        f"• Izoh: {escape(payment_note or 'Kiritilmagan')}\n\n"
        "Kerakli amalni tanlang."
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 Karta raqami", callback_data="admin_set_card"),
            InlineKeyboardButton("📝 To‘lov izohi", callback_data="admin_set_note"),
        ],
        [
            InlineKeyboardButton("👥 Referral tizimi", callback_data="admin_referral_settings"),
            InlineKeyboardButton("🔁 Majburiy obuna", callback_data="admin_toggle_subscription"),
        ],
        [
            InlineKeyboardButton("🪄 Hiyla tasdiqlash", callback_data="admin_toggle_fake_verify"),
            InlineKeyboardButton("⭐ Pullik obuna", callback_data="admin_toggle_premium"),
        ],
        [
            InlineKeyboardButton("🔁 Kino ulashish", callback_data="admin_toggle_share"),
            InlineKeyboardButton("🗑 Tark etganlar", callback_data="admin_cleanup_left_users"),
        ],
        [InlineKeyboardButton("🧹 Keshni tozalash", callback_data="admin_cleanup_cache")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_open")],
    ])
    await _reply(update, text, parse_mode="HTML", reply_markup=kb)


# ------------------------------------------------------------------
# RENDERERS
# ------------------------------------------------------------------
async def _render_channels_list() -> str:
    channels = await db.get_channels()
    if not channels:
        return "📭 Majburiy obuna ro‘yxati bo‘sh."

    lines = ["📋 <b>Majburiy obuna ro‘yxati</b>\n"]
    for i, ch in enumerate(channels, start=1):
        name = escape(str(ch.get("channel_name") or "Nomsiz"))
        row_id = escape(str(ch.get("id") or ""))
        channel_id = escape(str(ch.get("channel_id") or ""))
        channel_username = escape(str(ch.get("channel_username") or ""))
        channel_link = escape(str(ch.get("channel_link") or ""))

        lines.append(
            f"{i}. <b>{name}</b>\n"
            f"   №: <code>{row_id or '-'}</code>\n"
            f"   Telegram ID: <code>{channel_id or '-'}</code>\n"
            f"   Username: <code>{channel_username or '-'}</code>\n"
            f"   Link: {channel_link or '-'}"
        )

    return "\n\n".join(lines)


async def _render_promos_list() -> str:
    promos = await db.get_promo_links()
    if not promos:
        return "📭 Reklama linklar yo‘q."

    lines = ["🌐 <b>Reklama linklar ro‘yxati</b>\n"]
    for i, item in enumerate(promos, start=1):
        lines.append(
            f"{i}. ID: <code>{item['id']}</code>\n"
            f"   Nomi: <b>{escape(str(item.get('title') or '-'))}</b>\n"
            f"   URL: {escape(str(item.get('url') or '-'))}"
        )

    return "\n\n".join(lines)


async def _render_tariffs_list() -> str:
    tariffs = await db.get_tariffs()
    if not tariffs:
        return "📭 Tariflar yo‘q."

    lines = ["📦 <b>Tariflar ro‘yxati</b>\n"]
    for i, t in enumerate(tariffs, start=1):
        duration_days = int(t.get("duration_days", 0) or 0)
        vip = " ⭐ VIP" if int(t.get("is_vip", 0) or 0) == 1 else ""
        lines.append(
            f"{i}. ID: <code>{t.get('id')}</code>\n"
            f"   Nomi: <b>{escape(str(t.get('name') or ''))}{vip}</b>\n"
            f"   Narxi: {_format_money(t.get('price', 0))} so‘m\n"
            f"   Muddat: {duration_days} kun"
        )

    return "\n\n".join(lines)


async def _render_admins_list() -> str:
    admins = await db.get_admins()
    if not admins:
        return "📭 Adminlar ro‘yxati bo‘sh."

    lines = ["👮 <b>Adminlar ro‘yxati</b>\n"]
    for i, admin in enumerate(admins, start=1):
        username = admin.get("username")
        full_name = admin.get("full_name")

        block = f"{i}. ID: <code>{admin.get('user_id')}</code>"
        if username:
            block += f"\n   Username: @{escape(str(username))}"
        if full_name:
            block += f"\n   Ism: {escape(str(full_name))}"

        lines.append(block)

    return "\n\n".join(lines)


async def _render_stats() -> str:
    stats = await db.get_stats()
    users = int(stats.get("users", 0) or 0)
    premium_users = int(stats.get("premium_users", 0) or 0)
    today_users = int(stats.get("today_users", 0) or 0)
    movies = int(stats.get("movies", 0) or 0)
    views = int(stats.get("views", 0) or 0)
    channels = int(stats.get("channels", 0) or 0)
    promos = int(stats.get("promos", 0) or 0)

    inactive_users = max(users - premium_users, 0)
    bot_name = BOT_USERNAME if str(BOT_USERNAME).startswith("@") else f"@{BOT_USERNAME or 'KinoBot'}"

    return (
        "📊 <b>Statistika</b>\n"
        f"• Obunachilar soni: {users:,} ta\n"
        f"• Faol obunachilar: {premium_users:,} ta\n"
        f"• Tark etganlar: {inactive_users:,} ta\n"
        f"• Majburiy obuna kanallari: {channels:,} ta\n"
        f"• Reklama linklar: {promos:,} ta\n\n"
        "📈 <b>Faollik</b>\n"
        f"• Bugun qo‘shilganlar: +{today_users:,}\n"
        f"• Kinolar soni: {movies:,} ta\n"
        f"• Umumiy ko‘rishlar: {views:,} ta\n\n"
        f"🤖 <b>{bot_name}</b>"
    ).replace(",", " ")


async def _render_premium_users() -> str:
    users = await db.get_active_premium_users(limit=100)
    if not users:
        return "📭 Obuna olgan foydalanuvchilar yo‘q."

    lines = ["⭐ <b>Obuna olganlar ro‘yxati</b>\n"]
    for i, user in enumerate(users, start=1):
        username = f"@{escape(str(user['username']))}" if user.get("username") else "-"
        bought_at = _format_dt(user.get("bought_at"))
        expire_at = _format_dt(user.get("premium_expire"))
        remaining = _format_remaining_text(user.get("remaining_seconds"))
        tariff_name = escape(str(user.get("tariff_name") or "Noma’lum"))
        vip = " ⭐ VIP" if int(user.get("is_vip", 0) or 0) == 1 else ""

        lines.append(
            f"{i}. <code>{user['user_id']}</code> - {escape(str(user.get('full_name') or '-'))}\n"
            f"   Username: {username}\n"
            f"   Tarif: <b>{tariff_name}{vip}</b>\n"
            f"   Olgan vaqti: <b>{bought_at}</b>\n"
            f"   Tugash vaqti: <b>{expire_at}</b>\n"
            f"   Qoldi: <b>{remaining}</b>"
        )

    return "\n\n".join(lines)


async def _show_pending_payments(update: Update) -> None:
    payments = await db.get_pending_payments()
    if not payments:
        await _reply(update, "🧾 Kutilayotgan to‘lovlar yo‘q.", reply_markup=back_menu("admin_open"))
        return

    first = payments[0]
    username = first.get("username")
    vip = " ⭐ VIP" if int(first.get("is_vip", 0) or 0) == 1 else ""

    caption = (
        "🧾 <b>Yangi to‘lov</b>\n\n"
        f"ID: <code>{first['id']}</code>\n"
        f"User: <code>{first['user_id']}</code>\n"
        f"Ism: {escape(str(first.get('full_name') or '-'))}\n"
        f"Username: {'@' + escape(str(username)) if username else '-'}\n"
        f"Tarif: <b>{escape(str(first.get('tariff_name') or '-'))}{vip}</b>\n"
        f"Muddat: <b>{int(first.get('duration_days', 0) or 0)} kun</b>\n"
        f"Narx: <b>{_format_money(first.get('amount', 0))} so‘m</b>"
    )
    await _reply(update, caption, parse_mode="HTML", reply_markup=payment_review_kb(int(first["id"])))


# ------------------------------------------------------------------
# MOVIE HELPERS
# ------------------------------------------------------------------

async def _finalize_movie_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    code = context.user_data.get("new_movie_code")
    is_premium = bool(context.user_data.get("new_movie_is_premium", False))
    source_kind = str(context.user_data.get("new_movie_source_kind") or "copy")

    if not code:
        await _reply(update, "❌ Kino kodi topilmadi.", reply_markup=back_menu("admin_movies_menu"))
        return

    exists = await db.get_movie_by_code(code)
    if exists:
        await _reply(update, "❌ Bu kod bilan kino allaqachon mavjud.", reply_markup=back_menu("admin_movies_menu"))
        return

    if source_kind == "file":
        file_id = str(context.user_data.get("new_movie_file_id") or "")
        file_type = str(context.user_data.get("new_movie_file_type") or "video")
        if not file_id:
            await _reply(update, "❌ Video yoki document topilmadi.", reply_markup=back_menu("admin_movies_menu"))
            return
        await db.add_movie(
            code=code,
            title=code,
            description="",
            source_kind="file",
            source_file_id=file_id,
            source_file_type=file_type,
            is_premium=int(is_premium),
        )
        movie = await db.get_movie_by_code(code)
        _clear_admin_state(context)
        await _reply(
            update,
            "✅ <b>Kino saqlandi</b>\n\n"
            f"Kod: <code>{escape(str(movie['code']))}</code>\n"
            f"Manba: <code>file_id</code>\n"
            f"Turi: {'💎 Pullik kino' if int(movie.get('is_premium', 0) or 0) == 1 else '🎬 Oddiy kino'}",
            parse_mode="HTML",
            reply_markup=admin_movie_saved_kb(),
        )
        return

    if source_kind == "url":
        source_url = str(context.user_data.get("new_movie_source_url") or "").strip()
        if not source_url:
            await _reply(update, "❌ URL topilmadi.", reply_markup=back_menu("admin_movies_menu"))
            return
        await db.add_movie(
            code=code,
            title=code,
            description="🌐 Tashqi link orqali ko‘rish",
            source_kind="url",
            source_url=source_url,
            is_premium=int(is_premium),
        )
        movie = await db.get_movie_by_code(code)
        _clear_admin_state(context)
        await _reply(
            update,
            "✅ <b>Kino saqlandi</b>\n\n"
            f"Kod: <code>{escape(str(movie['code']))}</code>\n"
            f"Manba: <code>URL</code>\n"
            f"Turi: {'💎 Pullik kino' if int(movie.get('is_premium', 0) or 0) == 1 else '🎬 Oddiy kino'}",
            parse_mode="HTML",
            reply_markup=admin_movie_saved_kb(),
        )
        return

    source_chat_id = context.user_data.get("new_movie_source_chat_id")
    source_message_id = context.user_data.get("new_movie_source_message_id")

    if not source_chat_id or not source_message_id:
        await _reply(update, "❌ Kino ma’lumotlari to‘liq emas.", reply_markup=back_menu("admin_movies_menu"))
        return

    await db.add_movie(
        code=code,
        title=code,
        description="",
        source_chat_id=str(source_chat_id),
        source_message_id=int(source_message_id),
        source_kind="copy",
        is_premium=int(is_premium),
    )

    movie = await db.get_movie_by_code(code)
    if not movie:
        await _reply(update, "❌ Kino saqlandi, lekin bazadan topilmadi.", reply_markup=back_menu("admin_movies_menu"))
        return

    _clear_admin_state(context)
    await _reply(
        update,
        "✅ <b>Kino saqlandi</b>\n\n"
        f"Kod: <code>{escape(str(movie['code']))}</code>\n"
        f"Manba: <code>{escape(str(movie['source_chat_id']))}</code> / <code>{movie['source_message_id']}</code>\n"
        f"Turi: {'💎 Pullik kino' if int(movie.get('is_premium', 0) or 0) == 1 else '🎬 Oddiy kino'}",
        parse_mode="HTML",
        reply_markup=admin_movie_saved_kb(),
    )


async def _show_movie_edit_menu(update: Update, code: str) -> None:
    movie = await db.get_movie_by_code(code)
    if not movie:
        await _reply(update, "❌ Kino topilmadi.", reply_markup=back_menu("admin_movies_menu"))
        return

    text = (
        "✏️ <b>Kino tahrirlash</b>\n\n"
        f"Kod: <code>{escape(str(movie['code']))}</code>\n"
        f"Nomi: <b>{escape(str(movie.get('title') or '-'))}</b>\n"
        f"Ma’lumot: {escape(str(movie.get('description') or '-'))}\n"
        f"Holati: <b>{'💎 Pullik ko‘rinish' if int(movie.get('is_premium', 0) or 0) == 1 else '🔓 Ochiq ko‘rinish'}</b>"
    )
    await _reply(
        update,
        text,
        parse_mode="HTML",
        reply_markup=admin_movie_edit_kb(str(movie["code"]), int(movie.get("is_premium", 0) or 0)),
    )


# ------------------------------------------------------------------
# PAYMENT HELPERS
# ------------------------------------------------------------------
async def _handle_payment_approve(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_id: int,
) -> None:
    payment = await db.approve_payment(payment_id, admin_id=update.effective_user.id)
    if not payment:
        await _reply(update, "❌ To‘lov topilmadi yoki allaqachon ko‘rib chiqilgan.", reply_markup=back_menu("admin_payments"))
        return

    await _notify_user_payment_approved(context, payment)
    await _reply(
        update,
        "✅ <b>To‘lov tasdiqlandi!</b>\n\n"
        f"📦 <b>Tarif:</b> {escape(str(payment.get('tariff_name') or '-'))}\n"
        f"📆 <b>Muddat:</b> {int(payment.get('duration_days') or 0)} kun\n"
        f"👤 <b>Foydalanuvchi:</b> <code>{payment['user_id']}</code>\n"
        f"💰 <b>To‘lov summasi:</b> {_format_money(payment.get('amount', 0))} so‘m\n"
        f"⏰ <b>Sana:</b> {_format_dt(payment.get('reviewed_at'))}",
        parse_mode="HTML",
        reply_markup=back_menu("admin_payments"),
    )


async def _handle_payment_reject_done(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    payment_id: int,
    reason: str = "",
) -> None:
    payment = await db.reject_payment(payment_id, admin_id=update.effective_user.id, reason=reason)
    if payment:
        await _notify_user_payment_rejected(context, payment, reason=reason)

    text = f"❌ <b>To‘lov rad etildi</b>\n\nTo‘lov ID: <code>{payment_id}</code>"
    if reason and reason != "-":
        text += f"\nSabab: <b>{escape(reason)}</b>"

    await _reply(update, text, parse_mode="HTML", reply_markup=back_menu("admin_payments"))


# ------------------------------------------------------------------
# CLEANUP
# ------------------------------------------------------------------
async def _run_cleanup_left_users(update: Update) -> None:
    try:
        deleted_count = await db.cleanup_left_users()
        await _reply(
            update,
            f"✅ Tark etganlar tozalandi.\n\nO‘chirilganlar: <b>{deleted_count}</b>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_settings"),
        )
    except Exception:
        logger.exception("cleanup_left_users failed")
        await _reply(update, "❌ Tark etganlarni tozalashda xatolik yuz berdi.", reply_markup=back_menu("admin_settings"))


async def _run_cleanup_cache(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        context.user_data.clear()
        result = await db.cleanup_cache_data()
        await _reply(
            update,
            f"✅ Kesh tozalandi.\n\nNatija: <b>{result}</b>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_settings"),
        )
    except Exception:
        logger.exception("cleanup_cache_data failed")
        await _reply(update, "❌ Kesh tozalashda xatolik yuz berdi.", reply_markup=back_menu("admin_settings"))


# ------------------------------------------------------------------
# BROADCAST
# ------------------------------------------------------------------
async def _show_broadcast_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reklama preview: xabar matni + qo‘shilgan tugmalar (full-width) +
    pastida 📨 Yuborish tugmasi."""
    kind = context.user_data.get("broadcast_kind", "text")
    user_buttons = context.user_data.get("broadcast_buttons") or []
    kb = _broadcast_ready_kb(include_button=(kind == "text"), user_buttons=user_buttons)

    if kind == "text":
        text = context.user_data.get("broadcast_text", "")
        header = "📣 <b>Xabar preview</b>\n\n"
        footer = ""
        if user_buttons:
            footer = f"\n\n🎛 Qo‘shilgan tugmalar: <b>{len(user_buttons)} ta</b>"
        await _reply(
            update,
            f"{header}{escape(text)}{footer}\n\n📨 Yuborish uchun pastdagi tugmani bosing.",
            parse_mode="HTML",
            reply_markup=kb,
        )
    else:
        src_chat = context.user_data.get("broadcast_source_chat_id")
        src_msg = context.user_data.get("broadcast_source_message_id")
        try:
            if src_chat and src_msg:
                await context.bot.forward_message(
                    chat_id=update.effective_user.id,
                    from_chat_id=src_chat,
                    message_id=int(src_msg),
                )
        except Exception:
            logger.exception("preview forward failed")
        await _reply(
            update,
            "📣 <b>Forward xabar tayyor</b>\n\nYuqorida xabar preview ko‘rinishi.\n\n📨 Yuborish uchun pastdagi tugmani bosing.",
            parse_mode="HTML",
            reply_markup=kb,
        )


def _widen_text(text: str) -> str:
    """Telegram pufakchasini kengaytirish uchun ko‘rinmas to‘ldiruvchi qo‘shadi.
    Shu tarzda inline tugmalar ham keng (full-width) ko‘rinadi."""
    # \u2800 — Braille bo‘sh belgisi (ko‘rinmaydi, lekin kengligi bor, trim bo‘lmaydi)
    pad_line = "\u2800" * 35
    return f"{text or ''}\n\n{pad_line}"


async def _do_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kind = context.user_data.get("broadcast_kind", "text")
    users = await db.get_all_user_ids()
    ok = 0
    failed = 0

    reply_markup = None
    buttons = context.user_data.get("broadcast_buttons")
    if buttons:
        reply_markup = InlineKeyboardMarkup(buttons)

    text = context.user_data.get("broadcast_text")
    src_chat = context.user_data.get("broadcast_source_chat_id")
    src_msg = context.user_data.get("broadcast_source_message_id")

    if kind == "text" and not text:
        await _reply(update, "❌ Xabar matni topilmadi.", reply_markup=back_menu("admin_open"))
        return
    if kind == "forward" and (not src_chat or not src_msg):
        await _reply(update, "❌ Forward xabar topilmadi.", reply_markup=back_menu("admin_open"))
        return

    # Agar tugmalar bor bo‘lsa, pufakcha keng bo‘lishi uchun matnni to‘ldiramiz
    out_text = _widen_text(text) if (kind == "text" and reply_markup) else text

    for user_id in users:
        try:
            if kind == "text":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=out_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
            else:
                await context.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=src_chat,
                    message_id=int(src_msg),
                )
            ok += 1
        except Exception:
            failed += 1

    _clear_admin_state(context)
    await _reply(
        update,
        f"✅ Xabar yuborildi.\n\nYetib bordi: <b>{ok}</b>\nYetmadi: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=back_menu("admin_open"),
    )


# ------------------------------------------------------------------
# COMMANDS
# ------------------------------------------------------------------
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not await db.is_admin(update.effective_user.id):
        await _reply(update, "❌ Siz admin emassiz.")
        return
    await _show_admin_home(update, context)


async def admin_text_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.effective_user:
        return False
    if not await db.is_admin(update.effective_user.id):
        return False

    text = _extract_text(update).lower()

    if text in {"admin", "/admin", "panel", "admin panel"}:
        await _show_admin_home(update, context)
        return True

    if text in {"📊 statistika", "statistika"}:
        await _reply(update, await _render_stats(), parse_mode="HTML", reply_markup=admin_menu_reply_kb())
        return True

    if text in {"🧾 to‘lovlar", "🧾 to'lovlar", "to'lovlar", "to‘lovlar", "tolovlar"}:
        await _show_pending_payments(update)
        return True

    if text in {"📨 xabar yuborish", "xabar yuborish"}:
        _clear_admin_state(context)
        _set_state(context, STATE_BROADCAST_KIND)
        await _reply(update, "Foydalanuvchilarga yuboradigan xabar turini tanlang.", reply_markup=_broadcast_type_kb())
        return True

    if text in {"🎬 kinolar", "kinolar"}:
        await _show_movies_menu(update)
        return True

    if text in {"📢 kanallar", "📢 majburiy obuna", "majburiy obuna", "kanallar"}:
        await _show_channels_menu(update)
        return True

    if text in {"🌐 reklama linklar", "reklama linklar", "linklar"}:
        await _show_promos_menu(update)
        return True

    if text in {"💳 tariflar", "tariflar", "tarif"}:
        await _show_tariffs_menu(update)
        return True

    if text in {"⭐ obunachilar", "obunachilar"}:
        await _reply(update, await _render_premium_users(), parse_mode="HTML", reply_markup=admin_premium_actions_kb())
        return True

    if text in {"👮 adminlar", "adminlar"}:
        await _show_admins_menu(update)
        return True

    if text in {"⚙️ sozlamalar", "sozlamalar", "settings"}:
        await _show_settings_menu(update)
        return True

    if text in {"🔙 orqaga", "orqaga"}:
        _clear_admin_state(context)
        await update.message.reply_text("🏠 Bosh menyu", reply_markup=start_user_menu_kb())
        return True

    return False


# ------------------------------------------------------------------
# CALLBACK HANDLER
# ------------------------------------------------------------------
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    if not query or not update.effective_user:
        return False
    if not await db.is_admin(update.effective_user.id):
        return False

    data = query.data or ""
    await query.answer()

    if data == "admin_open":
        await _show_admin_home(update, context)
        return True
    if data == "admin_stats":
        await _reply(update, await _render_stats(), parse_mode="HTML", reply_markup=back_menu("admin_open"))
        return True
    if data == "admin_payments":
        await _show_pending_payments(update)
        return True
    if data == "admin_movies_menu":
        await _show_movies_menu(update)
        return True
    if data == "admin_channels_menu":
        await _show_channels_menu(update)
        return True
    if data == "admin_promos_menu":
        await _show_promos_menu(update)
        return True
    if data == "admin_tariffs_menu":
        await _show_tariffs_menu(update)
        return True
    if data == "admin_admins_menu":
        await _show_admins_menu(update)
        return True
    if data == "admin_settings":
        await _show_settings_menu(update)
        return True
    if data == "admin_premium_users":
        await _reply(update, await _render_premium_users(), parse_mode="HTML", reply_markup=admin_premium_actions_kb())
        return True

    if data == "admin_referral_settings":
        await _show_referral_settings(update)
        return True

    if data == "admin_toggle_referral":
        current = await db.get_setting("referral_enabled", "1")
        await db.set_setting("referral_enabled", "0" if str(current) == "1" else "1")
        await _show_referral_settings(update)
        return True

    if data == "admin_set_referral_price":
        _clear_admin_state(context)
        _set_state(context, STATE_SET_REFERRAL_PRICE)
        await _reply(update, "💰 Yangi referral narxini yuboring.\nMasalan: 300", reply_markup=admin_referral_price_kb())
        return True

    if data == "admin_referral_stats":
        try:
            stats = await db.get_referral_stats()
            top_users = await db.get_top_referrers(limit=10)
        except Exception:
            stats = {"total_referrals": 0, "active_referrals": 0, "total_bonus_paid": 0}
            top_users = []

        text = (
            "📊 <b>Referral statistikasi</b>\n\n"
            f"• Jami referallar: <b>{int(stats.get('total_referrals', 0) or 0):,}</b> ta\n"
            f"• Faol referallar: <b>{int(stats.get('active_referrals', 0) or 0):,}</b> ta\n"
            f"• To‘langan bonuslar: <b>{_format_money(stats.get('total_bonus_paid', 0))} so‘m</b>\n\n"
            "🏆 <b>Top referralchilar:</b>\n"
        ).replace(",", " ")

        if top_users:
            for i, user in enumerate(top_users, start=1):
                text += f"{i}. <code>{user['user_id']}</code> — {int(user.get('referral_count', 0) or 0)} ta\n"
        else:
            text += "Hali ma’lumot yo‘q."

        await _reply(update, text, parse_mode="HTML", reply_markup=back_menu("admin_referral_settings"))
        return True

    if data == "admin_add_movie":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_MOVIE_CODE)
        await _reply(
            update,
            "➕ <b>Kino qo‘shish</b>\n\nKino kodini yuboring.\nMasalan: <code>101</code>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data == "admin_delete_movie":
        _clear_admin_state(context)
        _set_state(context, STATE_DELETE_MOVIE_CODE)
        await _reply(
            update,
            "🗑 <b>Kino o‘chirish</b>\n\nO‘chiriladigan kino kodini yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data == "admin_edit_movie":
        _clear_admin_state(context)
        _set_state(context, STATE_EDIT_MOVIE_FIND)
        await _reply(
            update,
            "✏️ <b>Kino tahrirlash</b>\n\nTahrirlanadigan kino kodini yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data == "admin_movie_source_forward_info":
        context.user_data["new_movie_source_kind"] = "copy"
        _set_state(context, STATE_ADD_MOVIE_SOURCE)
        await _reply(update, "📨 Endi kanaldan forward qilingan postni yuboring.", reply_markup=back_menu("admin_movies_menu"))
        return True

    if data == "admin_movie_source_link_info":
        context.user_data["new_movie_source_kind"] = "copy"
        _set_state(context, STATE_ADD_MOVIE_SOURCE)
        await _reply(
            update,
            "🔗 Endi post ssilkasini yuboring.\nMasalan: <code>https://t.me/kanal/123</code>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data == "admin_movie_source_file_info":
        context.user_data["new_movie_source_kind"] = "file"
        _set_state(context, STATE_ADD_MOVIE_SOURCE)
        await _reply(update, "📁 Endi videoni yoki documentni botga yuboring.", reply_markup=back_menu("admin_movies_menu"))
        return True

    if data == "admin_movie_source_url_info":
        context.user_data["new_movie_source_kind"] = "url"
        _set_state(context, STATE_ADD_MOVIE_SOURCE)
        await _reply(
            update,
            "🌐 Endi tashqi ssilkani yuboring.\nMasalan: <code>https://example.com/movie</code>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data == "admin_movie_premium_yes":
        context.user_data["new_movie_is_premium"] = True
        await _finalize_movie_creation(update, context)
        return True

    if data == "admin_movie_premium_no":
        context.user_data["new_movie_is_premium"] = False
        await _finalize_movie_creation(update, context)
        return True

    if data.startswith("edit_movie_code:"):
        code = data.split(":", 1)[1]
        context.user_data["edit_movie_code_target"] = code
        _set_state(context, STATE_EDIT_MOVIE_CODE)
        await _reply(
            update,
            f"✏️ Eski kod: <code>{escape(code)}</code>\n\nYangi kodni yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data.startswith("edit_movie_name:"):
        code = data.split(":", 1)[1]
        context.user_data["edit_movie_code_target"] = code
        _set_state(context, STATE_EDIT_MOVIE_NAME)
        await _reply(
            update,
            f"✏️ Kino kodi: <code>{escape(code)}</code>\n\nYangi nomni yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data.startswith("edit_movie_caption:"):
        code = data.split(":", 1)[1]
        context.user_data["edit_movie_code_target"] = code
        _set_state(context, STATE_EDIT_MOVIE_CAPTION)
        await _reply(
            update,
            f"✏️ Kino kodi: <code>{escape(code)}</code>\n\nYangi ma’lumotni yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_movies_menu"),
        )
        return True

    if data.startswith("toggle_movie_access:"):
        code = data.split(":", 1)[1]
        movie = await db.get_movie_by_code(code)
        if not movie:
            await _reply(update, "❌ Kino topilmadi.")
            return True
        new_value = 0 if int(movie.get("is_premium", 0) or 0) == 1 else 1
        await db.update_movie_premium(code, new_value)
        await _show_movie_edit_menu(update, code)
        return True

    if data in ("admin_add_channel", "admin_add_channel_type"):
        _clear_admin_state(context)
        await _reply(
            update,
            "⚙️ <b>Majburiy obuna turini tanlang:</b>\n\n"
            "Quyida majburiy obunani qo‘shishning 3 ta turi mavjud:\n\n"
            "<blockquote>"
            "🔹 <b>Ommaviy / Shaxsiy (Kanal · Guruh)</b>\n"
            "Har qanday kanal yoki guruhni (ommaviy yoki shaxsiy) majburiy obunaga ulash.\n\n"
            "🔹 <b>Shaxsiy / So‘rovli havola</b>\n"
            "Shaxsiy yoki so‘rovli kanal/guruh havolasi orqali o‘tganlarni kuzatish.\n\n"
            "🔹 🌐 <b>Oddiy havola</b>\n"
            "Majburiy tekshiruvsiz oddiy havolani ko‘rsatish (Instagram, sayt va boshqalar)."
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=admin_channel_type_kb(),
        )
        return True

    if data == "admin_channel_type_public":
        _clear_admin_state(context)
        await _reply(
            update,
            "📢 <b>Ommaviy / Shaxsiy (Kanal · Guruh) - ulash</b>\n\n"
            "Quyida kanal/guruhni ulashning 3 ta oddiy usuli mavjud:\n\n"
            "<blockquote>"
            "🔹 <b>1. ID orqali ulash</b>\n"
            "Kanal yoki guruh ID raqamini kiriting.\n"
            "ID odatda <code>-100...</code> shaklida bo‘ladi.\n\n"
            "🔹 <b>2. Havola orqali ulash</b>\n"
            "Kanal/guruh havolasini yuboring.\n"
            "Masalan: <code>@kanal_nomi</code> yoki <code>https://t.me/kanal</code>\n\n"
            "🔹 <b>3. Postni ulash orqali</b>\n"
            "Kanal yoki guruhdan <b>bitta postni ulashing</b> va shu xabarni botga yuboring.\n"
            "Bot avtomatik ravishda kanalni taniydi."
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=admin_channel_public_methods_kb(),
        )
        return True

    if data == "admin_channel_type_private":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_CHANNEL_ID)
        await _reply(
            update,
            "🔐 <b>Shaxsiy / So‘rovli havola</b>\n\n"
            "<blockquote>"
            "Shaxsiy yoki so‘rovli kanal/guruh havolasini yuboring.\n\n"
            "Masalan:\n"
            "• <code>https://t.me/+AbCdEf123456</code>\n"
            "• <code>https://t.me/joinchat/AbCdEf...</code>\n\n"
            "Yoki shu kanaldan forward qilingan postni yuboring."
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_add_channel_type"),
        )
        return True

    if data == "admin_channel_type_simple":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_PROMO_TITLE)
        await _reply(
            update,
            "🌐 <b>Oddiy havola qo‘shish</b>\n\n"
            "<blockquote>"
            "Bu havola majburiy tekshiruvsiz oddiy havola sifatida qo‘shiladi (Instagram, YouTube, sayt va h.k.).\n\n"
            "Avval havola nomini yuboring.\nMasalan: <b>Instagram</b>"
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_add_channel_type"),
        )
        return True

    if data == "admin_channel_add_id":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_CHANNEL_ID)
        await _reply(
            update,
            "🆔 <b>ID orqali ulash</b>\n\n"
            "<blockquote>"
            "Kanal yoki guruh ID raqamini yuboring.\n"
            "Masalan: <code>-1001234567890</code>"
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_channel_type_public"),
        )
        return True

    if data == "admin_channel_add_link":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_CHANNEL_ID)
        await _reply(
            update,
            "🔗 <b>Havola orqali ulash</b>\n\n"
            "<blockquote>"
            "Kanal/guruh havolasini yuboring.\n\n"
            "Masalan:\n"
            "• <code>@kanal_nomi</code>\n"
            "• <code>https://t.me/kanal_nomi</code>"
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_channel_type_public"),
        )
        return True

    if data == "admin_channel_add_forward":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_CHANNEL_ID)
        await _reply(
            update,
            "📨 <b>Postni ulash orqali</b>\n\n"
            "<blockquote>"
            "Kanal yoki guruhdan istalgan bitta postni shu botga forward qiling.\n"
            "Bot avtomatik kanalni aniqlab oladi."
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=back_menu("admin_channel_type_public"),
        )
        return True

    if data == "admin_list_channels":
        await _reply(update, await _render_channels_list(), parse_mode="HTML", reply_markup=admin_channel_actions_kb())
        return True

    if data == "admin_delete_channel":
        _clear_admin_state(context)
        _set_state(context, STATE_DELETE_CHANNEL_ID)
        await _reply(update, "🗑 O‘chiriladigan kanal ID yoki ro‘yxatdagi ID ni yuboring.", reply_markup=back_menu("admin_channels_menu"))
        return True

    if data == "admin_add_promo":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_PROMO_TITLE)
        await _reply(
            update,
            "➕ <b>Reklama link</b>\n\nLink nomini yuboring.\nMasalan: Instagram",
            parse_mode="HTML",
            reply_markup=back_menu("admin_promos_menu"),
        )
        return True

    if data == "admin_list_promos":
        await _reply(update, await _render_promos_list(), parse_mode="HTML", reply_markup=admin_promo_actions_kb())
        return True

    if data == "admin_delete_promo":
        _clear_admin_state(context)
        _set_state(context, STATE_DELETE_PROMO_ID)
        await _reply(update, "🗑 O‘chiriladigan reklama link ID sini yuboring.", reply_markup=back_menu("admin_promos_menu"))
        return True

    if data == "admin_add_tariff":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_TARIFF_NAME)
        await _reply(update, "➕ Tarif nomini yuboring.", reply_markup=back_menu("admin_tariffs_menu"))
        return True

    if data == "admin_list_tariffs":
        await _reply(update, await _render_tariffs_list(), parse_mode="HTML", reply_markup=admin_tariff_saved_kb())
        return True

    if data == "admin_delete_tariff":
        _clear_admin_state(context)
        _set_state(context, STATE_DELETE_TARIFF_ID)
        await _reply(update, "🗑 O‘chiriladigan tarif ID sini yuboring.", reply_markup=back_menu("admin_tariffs_menu"))
        return True

    if data.startswith("admin_tariff_vip:"):
        try:
            context.user_data["new_tariff_is_vip"] = int(data.split(":")[1])
            tariff = await db.add_tariff(
                name=context.user_data["new_tariff_name"],
                duration_days=int(context.user_data["new_tariff_duration"]),
                price=int(context.user_data["new_tariff_price"]),
                is_vip=int(context.user_data["new_tariff_is_vip"]),
            )
        except Exception as e:
            logger.exception("add tariff error")
            await _reply(update, f"❌ Tarif saqlanmadi: {escape(str(e))}")
            return True

        _clear_admin_state(context)
        await _reply(
            update,
            f"✅ Tarif saqlandi: <b>{escape(str(tariff['name']))}</b>",
            parse_mode="HTML",
            reply_markup=admin_tariff_saved_kb(),
        )
        return True

    if data == "admin_add_admin":
        _clear_admin_state(context)
        _set_state(context, STATE_ADD_ADMIN_ID)
        await _reply(update, "➕ Qo‘shiladigan admin Telegram ID sini yuboring.", reply_markup=back_menu("admin_admins_menu"))
        return True

    if data == "admin_delete_admin":
        _clear_admin_state(context)
        _set_state(context, STATE_DELETE_ADMIN_ID)
        await _reply(update, "🗑 O‘chiriladigan admin Telegram ID sini yuboring.", reply_markup=back_menu("admin_admins_menu"))
        return True

    if data == "admin_list_admins":
        await _reply(update, await _render_admins_list(), parse_mode="HTML", reply_markup=admin_manage_done_kb())
        return True

    if data == "admin_set_card":
        _clear_admin_state(context)
        _set_state(context, STATE_SET_CARD)
        await _reply(update, "💳 Yangi karta raqamini yuboring.", reply_markup=back_menu("admin_settings"))
        return True

    if data == "admin_set_note":
        _clear_admin_state(context)
        _set_state(context, STATE_SET_NOTE)
        await _reply(update, "📝 Yangi to‘lov izohini yuboring.", reply_markup=back_menu("admin_settings"))
        return True

    if data == "admin_toggle_subscription":
        current = await db.get_setting("subscription_required", "1")
        await db.set_setting("subscription_required", "0" if str(current) == "1" else "1")
        await _show_settings_menu(update)
        return True

    if data == "admin_toggle_fake_verify":
        current = await db.get_setting("subscription_fake_verify", "1")
        await db.set_setting("subscription_fake_verify", "0" if str(current) == "1" else "1")
        await _show_settings_menu(update)
        return True

    if data == "admin_toggle_premium":
        current = await db.get_setting("premium_enabled", "1")
        await db.set_setting("premium_enabled", "0" if str(current) == "1" else "1")
        await _show_settings_menu(update)
        return True

    if data == "admin_toggle_share":
        current = await db.get_setting("movie_sharing_enabled", "1")
        await db.set_setting("movie_sharing_enabled", "0" if str(current) == "1" else "1")
        await _show_settings_menu(update)
        return True

    if data == "admin_cleanup_left_users":
        await _run_cleanup_left_users(update)
        return True

    if data == "admin_cleanup_cache":
        await _run_cleanup_cache(update, context)
        return True

    if data.startswith("approve_payment:"):
        await _handle_payment_approve(update, context, int(data.split(":")[1]))
        return True

    if data.startswith("reject_payment:"):
        context.user_data["reject_payment_id"] = int(data.split(":")[1])
        _set_state(context, STATE_WAIT_PAYMENT_REJECT_REASON)
        await _reply(
            update,
            "❌ Rad etish sababini yuboring. Istamasangiz <code>-</code> yuboring.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_payments"),
        )
        return True

    if data == "admin_revoke_premium":
        _clear_admin_state(context)
        _set_state(context, STATE_REVOKE_PREMIUM_USER_ID)
        await _reply(update, "➖ Premium olib qo‘yiladigan user ID sini yuboring.", reply_markup=back_menu("admin_premium_users"))
        return True

    # ---------- BROADCAST ----------
    if data == "broadcast_type_text":
        context.user_data["broadcast_kind"] = "text"
        context.user_data.pop("broadcast_text", None)
        context.user_data.pop("broadcast_buttons", None)
        context.user_data.pop("broadcast_buttons_text", None)
        _set_state(context, STATE_BROADCAST_TEXT)
        await _reply(update, "📣 Yuboriladigan reklama matnini yuboring.", reply_markup=back_menu("admin_open"))
        return True

    if data == "broadcast_type_forward":
        context.user_data["broadcast_kind"] = "forward"
        context.user_data.pop("broadcast_source_chat_id", None)
        context.user_data.pop("broadcast_source_message_id", None)
        _set_state(context, STATE_BROADCAST_FORWARD)
        await _reply(update, "📨 Endi forward qilinadigan xabarni yuboring.", reply_markup=back_menu("admin_open"))
        return True

    if data == "broadcast_add_button":
        if context.user_data.get("broadcast_kind") != "text":
            await _reply(update, "❌ Tugma qo‘shish faqat Oddiy xabar uchun ishlaydi.", reply_markup=_broadcast_ready_kb(include_button=False))
            return True
        _set_state(context, STATE_BROADCAST_BUTTONS)
        await _reply(
            update,
            "🎛 <b>Tugma qo‘shish</b>\n\n"
            "Tugma formatini shu tarzda yozing:\n"
            "<code>[Tugma matni|Tugma linki]</code>\n\n"
            "📝 <b>Namuna tugmalar:</b>\n"
            "🔹 <code>[Instagram|https://instagram.com]</code>\n"
            "🔹 <code>[Youtube|https://youtube.com]</code>\n"
            "🔹 <code>[Telegram|https://t.me]</code>\n\n"
            "❗️ Har bir tugma [Matn|Link] formatida bo‘lishi kerak. Link http, https yoki t.me bilan boshlanishi kerak.",
            parse_mode="HTML",
            reply_markup=back_menu("admin_open"),
        )
        return True

    if data == "broadcast_send":
        await _do_broadcast(update, context)
        return True

    return False


# ------------------------------------------------------------------
# MESSAGE HANDLER (text states)
# ------------------------------------------------------------------
async def admin_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not update.message or not update.effective_user:
        return False
    if not await db.is_admin(update.effective_user.id):
        return False

    state = _get_state(context)
    text = _extract_text(update)

    try:
        if state == STATE_ADD_MOVIE_CODE:
            if not text:
                await _reply(update, "❌ Kod yuboring.")
                return True

            code = _normalize_movie_code(text)
            if not code:
                await _reply(update, "❌ Kod bo‘sh bo‘lmasin.")
                return True

            context.user_data["new_movie_code"] = code
            _set_state(context, STATE_ADD_MOVIE_SOURCE)
            await _reply(
                update,
                "📥 Endi forward qilingan post yoki t.me post ssilkasini yuboring.",
                reply_markup=admin_add_movie_source_choose_kb(),
            )
            return True

        if state == STATE_ADD_MOVIE_SOURCE:
            source_kind = str(context.user_data.get("new_movie_source_kind") or "copy")

            if source_kind == "file":
                if update.message.video:
                    context.user_data["new_movie_file_id"] = update.message.video.file_id
                    context.user_data["new_movie_file_type"] = "video"
                    await _reply(update, "🎞 Kino turini tanlang.", reply_markup=admin_movie_type_kb())
                    return True
                if update.message.document:
                    context.user_data["new_movie_file_id"] = update.message.document.file_id
                    context.user_data["new_movie_file_type"] = "document"
                    await _reply(update, "🎞 Kino turini tanlang.", reply_markup=admin_movie_type_kb())
                    return True
                await _reply(update, "❌ Video yoki document yuboring.")
                return True

            if source_kind == "url":
                raw_url = text.strip()
                if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
                    await _reply(update, "❌ To‘g‘ri URL yuboring. Masalan: https://example.com/movie")
                    return True
                context.user_data["new_movie_source_url"] = raw_url
                await _reply(update, "🎞 Kino turini tanlang.", reply_markup=admin_movie_type_kb())
                return True

            source_chat_id = None
            source_message_id = None

            if getattr(update.message, "forward_date", None) or getattr(update.message, "forward_origin", None):
                source_chat_id, source_message_id = extract_forward_source_info(update.message)

            if not source_chat_id and text:
                source_chat_id, source_message_id = extract_message_link_info(text)

            if not source_chat_id or not source_message_id:
                await _reply(update, "❌ Forward qilingan post yoki to‘g‘ri t.me ssilka yuboring.")
                return True

            context.user_data["new_movie_source_chat_id"] = source_chat_id
            context.user_data["new_movie_source_message_id"] = source_message_id
            await _reply(update, "🎞 Kino turini tanlang.", reply_markup=admin_movie_type_kb())
            return True

        if state == STATE_DELETE_MOVIE_CODE:
            movie = await db.get_movie_by_code(text)
            if not movie:
                await _reply(update, "❌ Bunday kino topilmadi.", reply_markup=back_menu("admin_movies_menu"))
                return True
            await db.delete_movie(text)
            _clear_admin_state(context)
            await _reply(update, "✅ Kino o‘chirildi.", reply_markup=back_menu("admin_movies_menu"))
            return True

        if state == STATE_EDIT_MOVIE_FIND:
            movie = await db.get_movie_by_code(text)
            if not movie:
                await _reply(update, "❌ Kino topilmadi.", reply_markup=back_menu("admin_movies_menu"))
                return True
            await _show_movie_edit_menu(update, text)
            return True

        if state == STATE_EDIT_MOVIE_CODE:
            old_code = context.user_data.get("edit_movie_code_target")
            if not old_code:
                await _reply(update, "❌ Tahrirlash kodi topilmadi.")
                return True
            new_code = _normalize_movie_code(text)
            if not new_code:
                await _reply(update, "❌ Yangi kod bo‘sh bo‘lmasin.")
                return True
            await db.update_movie_code(old_code, new_code)
            _clear_admin_state(context)
            await _reply(update, "✅ Kino kodi yangilandi.", reply_markup=back_menu("admin_movies_menu"))
            return True

        if state == STATE_EDIT_MOVIE_NAME:
            code = context.user_data.get("edit_movie_code_target")
            if not code:
                await _reply(update, "❌ Kino kodi topilmadi.")
                return True
            await db.update_movie_title(code, text)
            _clear_admin_state(context)
            await _reply(update, "✅ Kino nomi yangilandi.", reply_markup=back_menu("admin_movies_menu"))
            return True

        if state == STATE_EDIT_MOVIE_CAPTION:
            code = context.user_data.get("edit_movie_code_target")
            if not code:
                await _reply(update, "❌ Kino kodi topilmadi.")
                return True
            await db.update_movie_description(code, text)
            _clear_admin_state(context)
            await _reply(update, "✅ Kino ma’lumoti yangilandi.", reply_markup=back_menu("admin_movies_menu"))
            return True

        if state == STATE_ADD_CHANNEL_ID:
            source_chat_id = None

            if getattr(update.message, "forward_date", None) or getattr(update.message, "forward_origin", None):
                source_chat_id, _ = extract_forward_source_info(update.message)

            raw = text
            username = ""
            link = ""

            if _is_external_social_url(raw):
                await _reply(update, "❌ Instagram / YouTube / boshqa tashqi linklar majburiy obunaga qo'shilmaydi. Ularni Reklama linklar bo'limiga qo'shing.", reply_markup=back_menu("admin_channels_menu"))
                return True

            if _is_private_telegram_invite(raw):
                await _reply(update, "❌ Private Telegram invite link majburiy obunaga yaramaydi. Public @username yoki public t.me link yuboring.", reply_markup=back_menu("admin_channels_menu"))
                return True

            if source_chat_id:
                raw = str(source_chat_id)
                try:
                    chat = await context.bot.get_chat(source_chat_id)
                    chat_username = str(getattr(chat, "username", "") or "").strip()
                    if chat_username:
                        username = f"@{chat_username}"
                        link = f"https://t.me/{chat_username}"
                except Exception:
                    pass
            elif raw.startswith(("https://t.me/", "http://t.me/", "t.me/")):
                link = raw if raw.startswith("http") else f"https://{raw}"
                match = re.search(r"t\.me/([A-Za-z0-9_]{4,})", link)
                if match:
                    username = f"@{match.group(1)}"
                    raw = username
            elif raw.startswith("@"):
                username = raw
                link = f"https://t.me/{raw[1:]}"
            elif re.fullmatch(r"-?\d+", raw):
                try:
                    chat = await context.bot.get_chat(raw)
                    chat_username = str(getattr(chat, "username", "") or "").strip()
                    if chat_username:
                        username = f"@{chat_username}"
                        link = f"https://t.me/{chat_username}"
                except Exception:
                    pass
            elif re.fullmatch(r"[A-Za-z0-9_]{4,}", raw):
                username = f"@{raw}"
                link = f"https://t.me/{raw}"
                raw = username

            context.user_data["new_channel_id"] = raw
            context.user_data["new_channel_username"] = username
            context.user_data["new_channel_link"] = link

            _set_state(context, STATE_ADD_CHANNEL_NAME)
            await _reply(
                update,
                "📝 Endi kanal nomini yuboring.\nMasalan: Asosiy kanal",
                reply_markup=back_menu("admin_channels_menu"),
            )
            return True

        if state == STATE_ADD_CHANNEL_NAME:
            raw_value = str(context.user_data.get("new_channel_id") or "").strip()
            if not raw_value:
                await _reply(update, "❌ Kanal qiymati topilmadi.")
                return True

            channel_username = str(context.user_data.get("new_channel_username") or "").strip()
            channel_link = str(context.user_data.get("new_channel_link") or "").strip()
            if not channel_username and not channel_link:
                await _reply(update, "❌ Bu kanal uchun foydalanuvchi bosadigan public Telegram link topilmadi. Public @username yoki public t.me link bilan qayta qo'shing.", reply_markup=back_menu("admin_channels_menu"))
                _clear_admin_state(context)
                return True

            try:
                channel = await db.add_channel(
                    channel_id=raw_value,
                    channel_name=text,
                    channel_username=channel_username,
                    channel_link=channel_link,
                )
            except Exception as e:
                await _reply(update, f"❌ Kanal qo'shib bo'lmadi:\n{escape(str(e))}", parse_mode="HTML", reply_markup=back_menu("admin_channels_menu"))
                return True
            _clear_admin_state(context)
            await _reply(
                update,
                "✅ <b>Kanal muvaffaqiyatli qo‘shildi</b>\n\n"
                f"📝 Nomi: <b>{escape(str(channel.get('channel_name') or '-'))}</b>\n"
                f"🆔 Qiymat: <code>{escape(raw_value)}</code>",
                parse_mode="HTML",
                reply_markup=admin_channel_actions_kb(),
            )
            return True

        if state == STATE_DELETE_CHANNEL_ID:
            await db.delete_channel(text)
            _clear_admin_state(context)
            await _reply(update, "✅ Kanal o‘chirildi.", reply_markup=admin_channel_actions_kb())
            return True

        if state == STATE_ADD_PROMO_TITLE:
            if not text:
                await _reply(update, "❌ Nom yuboring.")
                return True
            context.user_data["new_promo_title"] = text
            _set_state(context, STATE_ADD_PROMO_URL)
            await _reply(
                update,
                "🔗 Endi URL yuboring.\nMasalan: https://instagram.com/...",
                reply_markup=back_menu("admin_promos_menu"),
            )
            return True

        if state == STATE_ADD_PROMO_URL:
            if not text.startswith(("http://", "https://", "t.me/", "@")):
                await _reply(update, "❌ To‘g‘ri URL yuboring.")
                return True
            promo = await db.add_promo_link(context.user_data.get("new_promo_title"), text)
            _clear_admin_state(context)
            await _reply(
                update,
                f"✅ Reklama link qo‘shildi: <b>{escape(str(promo['title']))}</b>",
                parse_mode="HTML",
                reply_markup=admin_promo_actions_kb(),
            )
            return True

        if state == STATE_DELETE_PROMO_ID:
            await db.delete_promo_link(text)
            _clear_admin_state(context)
            await _reply(update, "✅ Reklama link o‘chirildi.", reply_markup=admin_promo_actions_kb())
            return True

        if state == STATE_ADD_TARIFF_NAME:
            if not text:
                await _reply(update, "❌ Tarif nomini yuboring.")
                return True
            context.user_data["new_tariff_name"] = text
            _set_state(context, STATE_ADD_TARIFF_PRICE)
            await _reply(update, "💰 Narxini yuboring.\nMasalan: 20000", reply_markup=back_menu("admin_tariffs_menu"))
            return True

        if state == STATE_ADD_TARIFF_PRICE:
            context.user_data["new_tariff_price"] = _parse_money(text)
            if int(context.user_data["new_tariff_price"]) <= 0:
                await _reply(update, "❌ Narx 0 dan katta bo‘lishi kerak.")
                return True
            _set_state(context, STATE_ADD_TARIFF_DURATION)
            await _reply(update, "📆 Muddatini kunlarda yuboring.\nMasalan: 30", reply_markup=back_menu("admin_tariffs_menu"))
            return True

        if state == STATE_ADD_TARIFF_DURATION:
            duration = _parse_int(text, "Muddat")
            if duration <= 0:
                await _reply(update, "❌ Muddat 0 dan katta bo‘lsin.")
                return True
            context.user_data["new_tariff_duration"] = duration
            _set_state(context, STATE_ADD_TARIFF_VIP)
            await _reply(update, "⭐ VIP yoki oddiy tarifligini tanlang.", reply_markup=admin_tariff_vip_kb())
            return True

        if state == STATE_DELETE_TARIFF_ID:
            tariff_id = _parse_int(text, "Tarif ID")
            await db.delete_tariff(tariff_id)
            _clear_admin_state(context)
            await _reply(update, "✅ Tarif o‘chirildi.", reply_markup=admin_tariff_saved_kb())
            return True

        if state == STATE_ADD_ADMIN_ID:
            admin_id = _parse_int(text, "Admin ID")
            await db.add_admin(admin_id)
            _clear_admin_state(context)
            await _reply(update, "✅ Admin qo‘shildi.", reply_markup=admin_manage_done_kb())
            return True

        if state == STATE_DELETE_ADMIN_ID:
            admin_id = _parse_int(text, "Admin ID")
            await db.delete_admin(admin_id)
            _clear_admin_state(context)
            await _reply(update, "✅ Admin o‘chirildi.", reply_markup=admin_manage_done_kb())
            return True

        if state == STATE_SET_CARD:
            if not text:
                await _reply(update, "❌ Karta raqami bo‘sh bo‘lmasin.")
                return True
            await db.set_setting("payment_card", text)
            _clear_admin_state(context)
            await _reply(update, "✅ Karta saqlandi.", reply_markup=back_menu("admin_settings"))
            return True

        if state == STATE_SET_NOTE:
            await db.set_setting("payment_note", text)
            _clear_admin_state(context)
            await _reply(update, "✅ To‘lov izohi saqlandi.", reply_markup=back_menu("admin_settings"))
            return True

        if state == STATE_SET_REFERRAL_PRICE:
            price = _parse_money(text)
            if price < 0:
                await _reply(update, "❌ Referral narxi manfiy bo‘lmasin.")
                return True
            await db.set_setting("referral_price", str(price))
            _clear_admin_state(context)
            await _reply(update, "✅ Referral narxi saqlandi.", reply_markup=back_menu("admin_referral_settings"))
            return True

        # ----- BROADCAST states -----
        if state == STATE_BROADCAST_TEXT:
            if not text:
                await _reply(update, "❌ Xabar bo‘sh bo‘lmasin.")
                return True
            context.user_data["broadcast_text"] = text
            await _show_broadcast_preview(update, context)
            return True

        if state == STATE_BROADCAST_FORWARD:
            src_chat, src_msg = None, None
            if getattr(update.message, "forward_date", None) or getattr(update.message, "forward_origin", None):
                src_chat, src_msg = extract_forward_source_info(update.message)
            if not src_chat or not src_msg:
                await _reply(update, "❌ Forward qilingan xabar yuboring.")
                return True
            context.user_data["broadcast_source_chat_id"] = src_chat
            context.user_data["broadcast_source_message_id"] = src_msg
            await _show_broadcast_preview(update, context)
            return True

        if state == STATE_BROADCAST_BUTTONS:
            try:
                buttons = _parse_buttons(text)
            except ValueError as e:
                await _reply(update, f"❌ {escape(str(e))}")
                return True
            context.user_data["broadcast_buttons"] = buttons
            _set_state(context, STATE_BROADCAST_TEXT)
            await _reply(update, f"✅ {len(buttons)} ta tugma qo‘shildi. Quyida yangilangan preview:")
            await _show_broadcast_preview(update, context)
            return True

        if state == STATE_WAIT_PAYMENT_REJECT_REASON:
            payment_id = int(context.user_data.get("reject_payment_id"))
            _clear_admin_state(context)
            await _handle_payment_reject_done(update, context, payment_id, text)
            return True

        if state == STATE_REVOKE_PREMIUM_USER_ID:
            user_id = _parse_int(text, "User ID")
            context.user_data["revoke_premium_user_id"] = user_id
            _set_state(context, STATE_REVOKE_PREMIUM_REASON)
            await _reply(
                update,
                "📝 Sababini yuboring. Istamasangiz <code>-</code> yuboring.",
                parse_mode="HTML",
                reply_markup=back_menu("admin_premium_users"),
            )
            return True

        if state == STATE_REVOKE_PREMIUM_REASON:
            user_id = int(context.user_data.get("revoke_premium_user_id"))
            reason = "" if text == "-" else text
            await db.revoke_user_premium(user_id)
            _clear_admin_state(context)
            await _notify_user_premium_revoked(context, user_id, reason)
            await _reply(update, "✅ Premium olib qo‘yildi.", reply_markup=back_menu("admin_premium_users"))
            return True

    except ValueError as e:
        await _reply(update, f"❌ {escape(str(e))}")
        return True
    except Exception as e:
        logger.exception("admin_message_handler error")
        await _reply(update, f"❌ Xatolik: {escape(str(e))}")
        return True

    return False

def _is_external_social_url(text: str) -> bool:
    raw = str(text or "").strip().lower()
    return any(x in raw for x in ("instagram.com", "youtube.com", "youtu.be", "tiktok.com", "facebook.com", "x.com", "twitter.com"))


def _is_private_telegram_invite(text: str) -> bool:
    raw = str(text or "").strip().lower()
    return raw.startswith("https://t.me/+") or raw.startswith("http://t.me/+") or raw.startswith("t.me/+") or "joinchat" in raw


