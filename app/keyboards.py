from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu(is_super=False):
    rows = [
        [InlineKeyboardButton("🤖 Bot yaratish", callback_data="create_bot")],
        [InlineKeyboardButton("📋 Mening botlarim", callback_data="my_bots")],
        [InlineKeyboardButton("💳 To'lov qilish", callback_data="pay_info")],
        [InlineKeyboardButton("ℹ️ Qo'llanma", callback_data="help")],
    ]
    if is_super:
        rows.insert(0, [InlineKeyboardButton("👑 Super Admin Panel", callback_data="super_panel")])
    return InlineKeyboardMarkup(rows)


def bot_type_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 Kino bot", callback_data="type_kino")],
        [InlineKeyboardButton("🧹 Reklama tozalovchi bot", callback_data="type_cleaner")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="home")],
    ])


def super_panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 Barcha botlar", callback_data="super_bots")],
        [InlineKeyboardButton("💳 To'lov cheklari", callback_data="super_payments")],
        [InlineKeyboardButton("📊 Statistika", callback_data="super_stats")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="home")],
    ])


def super_bot_actions(bot_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Yoqish", callback_data=f"sbot_on:{bot_id}"), InlineKeyboardButton("⏸ O'chirish", callback_data=f"sbot_off:{bot_id}")],
        [InlineKeyboardButton("🚫 Bloklash", callback_data=f"sbot_block:{bot_id}")],
        [InlineKeyboardButton("⬅️ Botlar ro'yxati", callback_data="super_bots")],
    ])


def payment_actions(payment_id, bot_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"pay_ok:{payment_id}:{bot_id}"), InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_no:{payment_id}")],
        [InlineKeyboardButton("⬅️ Orqaga", callback_data="super_payments")],
    ])


def owner_bot_actions(bot_id, bot_type):
    rows = [
        [InlineKeyboardButton("💳 Karta sozlash", callback_data=f"owner_card:{bot_id}")],
        [InlineKeyboardButton("💰 Narx sozlash", callback_data=f"owner_price:{bot_id}")],
        [InlineKeyboardButton("📸 Chek yuborish", callback_data=f"send_check:{bot_id}")],
    ]
    if bot_type == 'kino':
        rows += [[InlineKeyboardButton("🎬 Kino bot paneli", callback_data=f"owner_kino:{bot_id}")]]
    if bot_type == 'cleaner':
        rows += [[InlineKeyboardButton("👥 Odam qo'shish limiti", callback_data=f"owner_cleaner:{bot_id}")]]
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="my_bots")])
    return InlineKeyboardMarkup(rows)


def cleaner_limit_kb(bot_id):
    nums = [5,10,15,20,25,30]
    rows = []
    for i in range(0, len(nums), 2):
        rows.append([InlineKeyboardButton(f"{nums[i]} odam", callback_data=f"climit:{bot_id}:{nums[i]}"), InlineKeyboardButton(f"{nums[i+1]} odam", callback_data=f"climit:{bot_id}:{nums[i+1]}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"bot:{bot_id}")])
    return InlineKeyboardMarkup(rows)


def child_kino_admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="kino_add")],
        [InlineKeyboardButton("📊 Statistika", callback_data="kino_stats")],
        [InlineKeyboardButton("💳 Karta ma'lumoti", callback_data="kino_card")],
    ])
