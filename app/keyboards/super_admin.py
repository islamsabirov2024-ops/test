from app.keyboards.common import reply, inline

# =========================
# 👑 SUPER ADMIN PANEL
# =========================

def super_main():
    return reply([
        ["👑 Super Admin Panel"],
        ["🤖 Barcha botlar"],
        ["💳 To'lovlar"],
        ["📊 Umumiy statistika"],
        ["📨 Platforma xabari"],
        ["⚙️ Platforma sozlamalari"],
    ])

# =========================
# 👤 ODDIY USER PANEL
# =========================

def user_main():
    return reply([
        ["🤖 Bot yaratish"],
        ["📋 Mening botlarim"],
        ["💳 To'lov qilish"],
        ["ℹ️ Yordam"],
    ])

# =========================
# 🛠 BOT EGASI ADMIN PANEL
# =========================

def owner_main():
    return reply([
        ["🛠 Bot Egasi Panel"],
        ["🎬 Kinolar"],
        ["🔐 Majburiy obuna"],
        ["💳 Karta va to'lov"],
        ["💎 Premium"],
        ["📣 Reklama"],
        ["📊 Statistika"],
        ["👮 Adminlar"],
        ["⚙️ Sozlamalar"],
        ["📋 Mening botlarim"],
    ])

# =========================
# 🤖 BOT TANLASH
# =========================

def template_choice():
    return inline([
        [("🎬 Kino bot", "tpl:kino")],
        [("🧹 Reklama tozalovchi bot", "tpl:moderator")],
        [("🔙 Orqaga", "home")],
    ])

def my_bot_actions(bot_id: int, status: str):
    rows = [
        [("🛠 Admin panelga kirish", f"owner:open:{bot_id}")],
        [("ℹ️ Bot ma'lumoti", f"owner:info:{bot_id}")],
    ]

    if status == "active":
        rows.append([("⏸ Botni vaqtincha to'xtatish", f"owner:pause:{bot_id}")])
    else:
        rows.append([("💳 To'lov qilish", f"owner:pay:{bot_id}")])

    rows.append([("🔙 Orqaga", "home")])
    return inline(rows)

# =========================
# 👑 SUPER ADMIN BOT ACTIONS
# =========================

def bot_actions(bot_id: int, status: str):
    rows = []

    if status == "active":
        rows.append([("⏸ To'xtatish", f"sbot:pause:{bot_id}")])
    else:
        rows.append([("▶️ Ishga tushirish", f"sbot:active:{bot_id}")])

    rows += [
        [("🚫 Bloklash", f"sbot:blocked:{bot_id}")],
        [("ℹ️ Batafsil", f"sbot:info:{bot_id}")],
    ]

    return inline(rows)

def payment_actions(payment_id: int):
    return inline([
        [
            ("✅ Tasdiqlash", f"pay:ok:{payment_id}"),
            ("❌ Rad etish", f"pay:no:{payment_id}")
        ]
    ])

# =========================
# 🎬 KINO BOT MENYULARI
# =========================

def movies_menu(bot_id: int):
    return inline([
        [("➕ Kino qo'shish", f"movie:add:{bot_id}")],
        [("📋 Kinolar ro'yxati", f"movie:list:{bot_id}")],
        [("🗑 Kino o'chirish", f"movie:delete:{bot_id}")],
        [("⭐ Premium kino sozlash", f"movie:premium:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def channels_menu(bot_id: int, enabled: bool = False):
    status = "✅ Yoqilgan" if enabled else "❌ O'chirilgan"

    return inline([
        [(f"🔐 Majburiy obuna: {status}", f"channel:toggle:{bot_id}")],
        [("➕ Kanal qo'shish", f"channel:add:{bot_id}")],
        [("📋 Kanallar ro'yxati", f"channel:list:{bot_id}")],
        [("🗑 Kanal o'chirish", f"channel:delete:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def payment_menu(bot_id: int):
    return inline([
        [("💳 Karta qo'shish / almashtirish", f"card:set:{bot_id}")],
        [("👤 Karta egasini yozish", f"card:owner:{bot_id}")],
        [("💰 Bot narxini sozlash", f"price:set:{bot_id}")],
        [("📋 To'lov ma'lumoti", f"card:info:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def premium_menu(bot_id: int, enabled: bool = False):
    # ✅ FIX: String yakuni " bilan yopildi (avval ' edi)
    status = "✅ Yoqilgan" if enabled else "❌ O'chirilgan"

    return inline([
        [(f"💎 Premium: {status}", f"premium:toggle:{bot_id}")],
        [("➕ Tarif qo'shish", f"premium:tariff_add:{bot_id}")],
        [("📋 Tariflar", f"premium:tariffs:{bot_id}")],
        [("👥 Premium foydalanuvchilar", f"premium:users:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def ads_menu(bot_id: int, enabled: bool = False):
    status = "✅ Yoqilgan" if enabled else "❌ O'chirilgan"

    return inline([
        [(f"📣 Reklama: {status}", f"ads:toggle:{bot_id}")],
        [("➕ Reklama qo'shish", f"ads:add:{bot_id}")],
        [("📋 Reklamalar", f"ads:list:{bot_id}")],
        [("🗑 Reklama o'chirish", f"ads:delete:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def settings_menu(bot_id: int):
    return inline([
        [("👋 Start matnini sozlash", f"settings:welcome:{bot_id}")],
        [("💳 To'lov matnini sozlash", f"settings:payment_text:{bot_id}")],
        [("🧹 Botni tozalash", f"settings:cleanup:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])

def admins_menu(bot_id: int):
    return inline([
        [("➕ Admin qo'shish", f"admin:add:{bot_id}")],
        [("📋 Adminlar ro'yxati", f"admin:list:{bot_id}")],
        [("🗑 Admin o'chirish", f"admin:delete:{bot_id}")],
        [("🔙 Orqaga", f"owner:open:{bot_id}")],
    ])
