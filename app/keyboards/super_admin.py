from app.keyboards.common import reply, inline


def super_main():
    return reply([
        ["👑 Super Admin Panel"],
        ["🤖 Barcha botlar"],
        ["💳 To‘lovlar"],
        ["📊 Umumiy statistika"],
        ["📨 Platforma xabari"],
    ])


def user_main():
    return reply([
        ["🤖 Bot yaratish"],
        ["📋 Mening botlarim"],
        ["💳 To‘lov qilish"],
        ["ℹ️ Yordam"],
    ])


def template_choice():
    return inline([
        [("🎬 Kino bot", "tpl:kino")],
        [("🧹 Reklama tozalovchi bot", "tpl:moderator")],
        [("🔙 Orqaga", "home")],
    ])


def bot_actions(bot_id:int, status:str):
    rows=[]
    if status == 'active': rows.append([("⏸ To‘xtatish", f"sbot:pause:{bot_id}")])
    else: rows.append([("▶️ Ishga tushirish", f"sbot:active:{bot_id}")])
    rows += [[("🚫 Bloklash", f"sbot:blocked:{bot_id}")],[("ℹ️ Batafsil", f"sbot:info:{bot_id}")]]
    return inline(rows)


def payment_actions(payment_id:int):
    return inline([[("✅ Tasdiqlash", f"pay:ok:{payment_id}"), ("❌ Rad etish", f"pay:no:{payment_id}")]])
