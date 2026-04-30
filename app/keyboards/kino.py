from app.keyboards.common import reply, inline


def user_menu():
    return reply([
        ["🎬 Kino kod yuborish"],
        ["💎 Premium"],
        ["📢 Kanallar"],
        ["ℹ️ Yordam"],
    ])


def admin_menu():
    return reply([
        ["📊 Statistika"],
        ["🎬 Kinolar", "🔐 Kanallar"],
        ["💳 To‘lov tizimlari", "💎 Premium"],
        ["📣 Reklama", "📨 Xabar yuborish"],
        ["👮 Adminlar", "⚙️ Sozlamalar"],
    ])


def movies_menu():
    return inline([
        [("➕ Kino qo‘shish", "movie:add")],
        [("📋 Kinolar ro‘yxati", "movie:list")],
        [("🗑 Kino o‘chirish", "movie:delete")],
        [("🔙 Orqaga", "admin:home")],
    ])


def channels_menu(force_enabled: str='0'):
    on = "✅ Yoniq" if force_enabled == '1' else "❌ O‘chiq"
    return inline([
        [(f"🔐 Majburiy obuna: {on}", "set:toggle:force_sub_enabled")],
        [("➕ Kanal qo‘shish", "channel:add")],
        [("📋 Kanallar ro‘yxati", "channel:list")],
        [("🗑 Kanal o‘chirish", "channel:delete")],
        [("🔙 Orqaga", "admin:home")],
    ])


def payments_menu():
    return inline([
        [("💳 Karta qo‘shish/almashtirish", "payset:card")],
        [("💰 Oylik narx sozlash", "payset:price")],
        [("📋 To‘lov ma’lumotlari", "payset:info")],
        [("🔙 Orqaga", "admin:home")],
    ])


def premium_menu(enabled='0'):
    on="✅ Yoniq" if enabled=='1' else "❌ O‘chiq"
    return inline([
        [(f"💎 Premium: {on}", "set:toggle:premium_enabled")],
        [("🎬 Kinoni premium qilish", "premium:mark")],
        [("🔙 Orqaga", "admin:home")],
    ])


def ads_menu(enabled='0'):
    on="✅ Yoniq" if enabled=='1' else "❌ O‘chiq"
    return inline([[(f"📣 Reklama: {on}", "set:toggle:ads_enabled")],[("✍️ Reklama matni", "ads:text")],[("🔙 Orqaga", "admin:home")]])


def settings_menu():
    return inline([
        [("👋 Start matnini o‘zgartirish", "text:welcome")],
        [("💳 To‘lov matnini o‘zgartirish", "text:payment")],
        [("🔙 Orqaga", "admin:home")],
    ])


def subscribe_kb(channels):
    rows=[]
    for ch in channels:
        if ch.get('link'): rows.append([(f"📢 {ch.get('title') or 'Kanal'}", ch['link'])])
    rows.append([("✅ Tekshirish", "sub:check")])
    return inline(rows)
