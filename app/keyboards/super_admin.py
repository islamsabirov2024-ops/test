from app.keyboards.common import reply, inline


def super_main():
    return reply([
        ["📊 Statistika", "📨 Xabar yuborish"],
        ["🎬 Kontent boshqaruvi", "🔐 Kanallar"],
        ["⚙️ Tizim sozlamalari", "📥 So‘rovlar"],
        ["👥 Foydalanuvchilar", "🤖 Barcha botlar"],
    ])


def user_main():
    return reply([
        ["➕ Bot yaratish", "🤖 Botlarim"],
        ["🗣 Referal", "📱 Shaxsiy kabinet"],
        ["🚀 Saytga kirish", "💳 Hisob to'ldirish"],
        ["📨 Murojaat", "📚 Qo'llanma"],
    ])


def template_choice():
    return inline([
        [("🎬 Kino Bot", "tpl:kino")],
        [("🚀 Nakrutka Bot", "tpl:nakrutka")],
        [("💵 Pul Bot", "tpl:pul")],
        [("📥 OpenBudget Bot", "tpl:openbudget")],
        [("🛍 Mahsulot Bot", "tpl:mahsulot")],
        [("🔐 VipKanal Bot", "tpl:vipkanal")],
        [("🚀 Smm Bot [💎 PREMIUM]", "tpl:smm")],
        [("🎥 ProKino Bot [💎 PREMIUM]", "tpl:prokino")],
        [("🔙 Orqaga", "home")],
    ])


def kino_tariff():
    return inline([
        [("💳 Tariflar ro‘yxati", "tariffs:kino")],
        [("✅ Bot yaratish — 9 000 so'm", "create:kino")],
        [("⏪ Orqaga", "home")],
    ])


def bot_actions(bot_id:int, status:str):
    rows=[]
    if status == 'active':
        rows.append([("⏸ To‘xtatish", f"sbot:pause:{bot_id}")])
    else:
        rows.append([("▶️ Ishga tushirish", f"sbot:active:{bot_id}")])
    rows += [[("🚫 Bloklash", f"sbot:blocked:{bot_id}")],[("ℹ️ Batafsil", f"sbot:info:{bot_id}")]]
    return inline(rows)


def payment_actions(payment_id:int):
    return inline([[('✅ Tasdiqlash', f'pay:ok:{payment_id}'), ('❌ Rad etish', f'pay:no:{payment_id}')]])


def pay_methods():
    return inline([
        [("⚪ Payme (Avto)", "paymethod:payme")],
        [("🔵 Click (Avto)", "paymethod:click")],
        [("💳 Karta (Avto)", "paymethod:karta")],
        [("💳 Humo", "paymethod:humo")],
    ])
