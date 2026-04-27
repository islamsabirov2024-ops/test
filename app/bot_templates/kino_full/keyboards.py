from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def _one(text: str, cb: str):
    return [InlineKeyboardButton(text, callback_data=cb)]


def _two(lt: str, lc: str, rt: str, rc: str):
    return [InlineKeyboardButton(lt, callback_data=lc), InlineKeyboardButton(rt, callback_data=rc)]


def _rows2(items, back_text: str = "🔙 Orqaga", back_cb: str = "admin_open"):
    """Inline menyularni asosiy menyudagidek 2 tadan joylaydi."""
    rows = []
    for i in range(0, len(items), 2):
        pair = items[i:i + 2]
        if len(pair) == 2:
            rows.append(_two(pair[0][0], pair[0][1], pair[1][0], pair[1][1]))
        else:
            rows.append(_one(pair[0][0], pair[0][1]))
    rows.append(_one(back_text, back_cb))
    return InlineKeyboardMarkup(rows)


# ==================================================================
# USER KEYBOARDS
# ==================================================================
def start_user_menu_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎬 Kino kodini yuborish")],
            [KeyboardButton("⭐ Premium obuna")],
            [KeyboardButton("👥 Referral")],
            [KeyboardButton("ℹ️ Yordam")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Kino kodini yuboring...",
    )


def help_menu_kb():
    return InlineKeyboardMarkup([
        _one("🎬 Kino qanday olinadi", "help_movie_code"),
        _one("💳 Premium qanday ishlaydi", "help_premium"),
        _one("🔙 Orqaga", "back_start"),
    ])


def premium_buy_kb():
    return InlineKeyboardMarkup([
        _one("💳 Obuna sotib olish", "buy_menu"),
        _one("🔙 Orqaga", "back_start"),
    ])


def tariffs_kb(tariffs):
    rows = []
    for t in tariffs:
        vip = " ⭐ VIP" if int(t.get("is_vip", 0) or 0) == 1 else ""
        text = f"💳 {t['name']}{vip} — {int(t['price']):,} so‘m ({int(t['duration_days'])} kun)".replace(",", " ")
        rows.append(_one(text, f"buy_tariff:{t['id']}"))
    rows.append(_one("🔙 Orqaga", "back_start"))
    return InlineKeyboardMarkup(rows)


# ==================================================================
# ADMIN MAIN MENU
# ==================================================================
def admin_menu_reply_kb():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📊 Statistika"), KeyboardButton("📨 Xabar yuborish")],
            [KeyboardButton("🎬 Kinolar"), KeyboardButton("📢 Kanallar")],
            [KeyboardButton("👮 Adminlar"), KeyboardButton("⚙️ Sozlamalar")],
            [KeyboardButton("💳 Tariflar"), KeyboardButton("⭐ Obunachilar")],
            [KeyboardButton("🔙 Orqaga")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin bo‘limini tanlang...",
    )


def back_menu(cb: str = "admin_open"):
    return InlineKeyboardMarkup([_one("⏪ Orqaga", cb)])


# ==================================================================
# MOVIES
# ==================================================================
def admin_movies_menu_kb():
    return _rows2([
        ("➕ Kino qo‘shish", "admin_add_movie"),
        ("✏️ Kino tahrirlash", "admin_edit_movie"),
        ("🗑 Kino o‘chirish", "admin_delete_movie"),
    ], "🔙 Orqaga", "admin_open")

def admin_add_movie_source_choose_kb():
    return _rows2([
        ("📨 Forward qilingan post", "admin_movie_source_forward_info"),
        ("🔗 Post ssilkasi", "admin_movie_source_link_info"),
        ("📁 Botga kino yuborish", "admin_movie_source_file_info"),
        ("🌐 Tashqi ssilka qo‘shish", "admin_movie_source_url_info"),
    ], "🔙 Orqaga", "admin_movies_menu")

def admin_movie_type_kb():
    return InlineKeyboardMarkup([
        _two("⭐ Pullik kino", "admin_movie_premium_yes", "🎬 Oddiy kino", "admin_movie_premium_no"),
        _one("🔙 Orqaga", "admin_movies_menu"),
    ])


def admin_movie_saved_kb():
    return InlineKeyboardMarkup([
        _one("➕ Yana kino qo‘shish", "admin_add_movie"),
        _one("🎬 Kinolar bo‘limi", "admin_movies_menu"),
        _one("🏠 Admin panel", "admin_open"),
    ])


def admin_movie_edit_kb(code: str, is_premium: int):
    status_text = "🔓 Bepul qilish" if int(is_premium or 0) == 1 else "💎 Pullik qilish"
    return InlineKeyboardMarkup([
        _two("✏️ Kod", f"edit_movie_code:{code}", "✏️ Nomi", f"edit_movie_name:{code}"),
        _two("📝 Ma’lumot", f"edit_movie_caption:{code}", status_text, f"toggle_movie_access:{code}"),
        _one("🔙 Orqaga", "admin_movies_menu"),
    ])


# ==================================================================
# CHANNELS (majburiy obuna)
# ==================================================================
def admin_channels_menu_kb():
    return _rows2([
        ("📣 Kanal qo‘shish", "admin_add_channel_type"),
        ("📋 Ro‘yxatni ko‘rish", "admin_list_channels"),
        ("🗑 Kanalni o‘chirish", "admin_delete_channel"),
        ("🌐 Reklama linklar", "admin_promos_menu"),
    ], "🔙 Orqaga", "admin_open")

def admin_channel_actions_kb():
    return _rows2([
        ("➕ Yana kanal qo‘shish", "admin_add_channel_type"),
        ("📋 Ro‘yxatni ko‘rish", "admin_list_channels"),
        ("🗑 Kanal o‘chirish", "admin_delete_channel"),
    ], "🔙 Orqaga", "admin_channels_menu")

def admin_channel_type_kb():
    return _rows2([
        ("📢 Public kanal/guruh", "admin_channel_type_public"),
        ("🔐 Private/so‘rovli", "admin_channel_type_private"),
        ("🌐 Oddiy havola", "admin_channel_type_simple"),
    ], "🔙 Orqaga", "admin_channels_menu")

def admin_channel_public_methods_kb():
    return _rows2([
        ("🆔 ID orqali ulash", "admin_channel_add_id"),
        ("🔗 Havola orqali ulash", "admin_channel_add_link"),
        ("📨 Postni ulash", "admin_channel_add_forward"),
    ], "🔙 Orqaga", "admin_add_channel_type")


# ==================================================================
# PROMO LINKS (reklama linklar)
# ==================================================================
def admin_promos_menu_kb():
    return _rows2([
        ("➕ Havola qo‘shish", "admin_add_promo"),
        ("📋 Havolalar ro‘yxati", "admin_list_promos"),
        ("🗑 Havolani o‘chirish", "admin_delete_promo"),
    ], "🔙 Orqaga", "admin_channels_menu")

def admin_promo_actions_kb():
    return _rows2([
        ("➕ Yana havola qo‘shish", "admin_add_promo"),
        ("📋 Havolalar ro‘yxati", "admin_list_promos"),
        ("🗑 Havolani o‘chirish", "admin_delete_promo"),
    ], "🔙 Orqaga", "admin_promos_menu")


# ==================================================================
# TARIFFS
# ==================================================================
def admin_tariffs_menu_kb():
    return _rows2([
        ("➕ Tarif qo‘shish", "admin_add_tariff"),
        ("📋 Premium tariflar", "admin_list_tariffs"),
        ("🗑 Tarif o‘chirish", "admin_delete_tariff"),
    ], "🔙 Orqaga", "admin_open")

def admin_tariff_vip_kb():
    return InlineKeyboardMarkup([
        _two("⭐ VIP", "admin_tariff_vip:1", "🎬 Oddiy", "admin_tariff_vip:0"),
        _one("🔙 Orqaga", "admin_tariffs_menu"),
    ])


def admin_tariff_saved_kb():
    return InlineKeyboardMarkup([
        _one("➕ Yana tarif", "admin_add_tariff"),
        _one("📋 Tariflar", "admin_list_tariffs"),
        _one("🔙 Orqaga", "admin_tariffs_menu"),
    ])


# ==================================================================
# PREMIUM USERS
# ==================================================================
def admin_premium_actions_kb():
    return _rows2([
        ("🧾 To‘lovlar", "admin_payments"),
        ("👥 Premium foydalanuvchilar", "admin_premium_users"),
        ("➖ Premium olib qo‘yish", "admin_revoke_premium"),
    ], "🔙 Orqaga", "admin_open")


# ==================================================================
# ADMINS
# ==================================================================
def admin_admins_menu_kb():
    return _rows2([
        ("➕ Admin qo‘shish", "admin_add_admin"),
        ("🗑 Admin o‘chirish", "admin_delete_admin"),
        ("📋 Adminlar ro‘yxati", "admin_list_admins"),
    ], "🔙 Orqaga", "admin_open")

def admin_manage_done_kb():
    return InlineKeyboardMarkup([_one("🏠 Admin panel", "admin_open")])


# ==================================================================
# REFERRAL
# ==================================================================
def admin_referral_settings_kb():
    return _rows2([
        ("🔁 Referral yoq/o‘chir", "admin_toggle_referral"),
        ("💰 Referral narxi", "admin_set_referral_price"),
        ("📊 Referral statistikasi", "admin_referral_stats"),
    ], "🔙 Orqaga", "admin_settings")

def admin_referral_price_kb():
    return InlineKeyboardMarkup([
        _one("🔙 Orqaga", "admin_referral_settings"),
    ])


# ==================================================================
# PAYMENTS / BROADCAST
# ==================================================================
def payment_review_kb(payment_id: int):
    return InlineKeyboardMarkup([
        _two("✅ Tasdiqlash", f"approve_payment:{payment_id}", "❌ Rad etish", f"reject_payment:{payment_id}"),
        _one("🔙 Orqaga", "admin_open"),
    ])


def broadcast_confirm_kb():
    return InlineKeyboardMarkup([
        _one("✅ Yuborishni boshlash", "broadcast_send"),
        _one("❌ Bekor qilish", "admin_open"),
    ])
