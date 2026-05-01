from app.keyboards.common import reply, inline


def user_menu():
    return reply([
        ["🎬 Kino kod yuborish"],
        ["💎 Premium", "📢 Kanallar"],
        ["ℹ️ Yordam"],
    ])


def admin_menu():
    return reply([
        ["📊 Statistika", "📨 Xabar yuborish"],
        ["🎬 Kontent boshqaruvi", "🔐 Kanallar"],
        ["⚙️ Tizim sozlamalari", "📥 So‘rovlar"],
        ["👥 Foydalanuvchilar", "💎 Premium"],
    ])


def content_menu():
    return reply([
        ["🎬 Kinolar", "📮 Postlar"],
        ["🔗 Referal"],
        ["⏪ Asosiy panel"],
    ])


def movies_menu():
    return reply([
        ["📥 Kino yuklash"],
        ["📝 Kino tahrirlash", "🗑 Kino o‘chirish"],
        ["📋 Kinolar ro‘yxati"],
        ["⬅️ Orqaga"],
    ])


def channels_menu_reply():
    return reply([
        ["➕ Kanal qo‘shish"],
        ["📋 Ro‘yxatni ko‘rish"],
        ["🗑 Kanalni o‘chirish"],
        ["⬅️ Orqaga"],
    ])


def payments_menu():
    return inline([
        [("💳 Karta qo‘shish/almashtirish", "payset:card")],
        [("💰 Oylik narx sozlash", "payset:price")],
        [("📋 To‘lov ma’lumotlari", "payset:info")],
        [("🔙 Orqaga", "admin:home")],
    ])


def premium_menu(enabled='0'):
    on="✅ Faol" if enabled=='1' else "❌ O‘chiq"
    return inline([
        [(f"💡 Holat o‘zgartirish — {on}", "set:toggle:premium_enabled")],
        [("👥 Premium foydalanuvchilar ro‘yxati", "premium:users")],
        [("📋 Premium tariflar", "premium:tariffs")],
        [("➕ Premium berish / Muddatni boshqarish", "premium:mark")],
        [("🔙 Orqaga", "admin:home")],
    ])


def ads_menu(enabled='0'):
    on="✅ Faol" if enabled=='1' else "❌ O‘chiq"
    return inline([[(f"📣 Reklama: {on}", "set:toggle:ads_enabled")],[("✍️ Reklama matni", "ads:text")],[("🔙 Orqaga", "admin:home")]])


def settings_menu():
    return reply([
        ["📣 Reklama", "👮 Adminlar"],
        ["↗️ Ulashish", "📝 Matnlar"],
        ["💳 To'lov tizimlar", "⚙️ Premium"],
        ["⏪ Asosiy panel"],
    ])


def subscribe_kb(channels):
    rows=[]
    for ch in channels:
        if ch.get('link'):
            rows.append([(f"📢 {ch.get('title') or 'Kanal'}", ch['link'])])
    rows.append([("✅ Tekshirish", "sub:check")])
    return inline(rows)
