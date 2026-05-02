from app.keyboards.common import reply, inline


def user_main():
    # ASOSIY MULTIBOT — botlarni boshqaradigan bot menyusi
    return reply([
        ['➕ Bot yaratish', '🤖 Botlarim'],
        ['🗣 Referal', '📱 Shaxsiy kabinet'],
        ['🚀 Saytga kirish', "💳 Hisob to'ldirish"],
        ['📨 Murojaat', "📚 Qo'llanma"],
    ])


def super_main():
    return reply([
        ['📊 Umumiy statistika', '📨 Xabar yuborish'],
        ['🤖 Barcha botlar', '💳 To‘lovlar'],
        ['⚙️ Global sozlamalar', '👥 Foydalanuvchilar'],
        ['⏪ Orqaga'],
    ])


def template_choice():
    return inline([
        [('🎬 Kino Bot', 'tpl:kino')],
        [('🚀 Nakrutka Bot', 'tpl:nakrutka')],
        [('💵 Pul Bot', 'tpl:pul')],
        [('📥 OpenBudget Bot', 'tpl:openbudget')],
        [('🛍 Mahsulot Bot', 'tpl:mahsulot')],
        [('🔐 VipKanal Bot', 'tpl:vipkanal')],
        [('🚀 Smm Bot [💎 PREMIUM]', 'tpl:smm')],
        [('🎥 ProKino Bot [💎 PREMIUM]', 'tpl:prokino')],
        [('🔙 Orqaga', 'home')],
    ])


def kino_tariff():
    return inline([
        [("💳 Tariflar ro'yxati", 'tariffs:kino')],
        [("✅ Bot yaratish — 9 000 so'm", 'create:kino')],
        [('⏪ Orqaga', 'home')],
    ])


def pay_methods():
    return inline([
        [('⚪ Payme (Avto)', 'paymethod:payme')],
        [('🔵 Click (Avto)', 'paymethod:click')],
        [('💳 Karta (Avto)', 'paymethod:karta')],
        [('💳 Humo', 'paymethod:humo')],
    ])


def bot_actions(bot_id: int, status: str):
    rows = []
    if status == 'active':
        rows.append([('⏸ To‘xtatish', f'sbot:pause:{bot_id}')])
    else:
        rows.append([('▶️ Ishga tushirish', f'sbot:active:{bot_id}')])
    rows += [
        [('🔑 Token almashtirish', f'sbot:token:{bot_id}')],
        [('🚫 Bloklash', f'sbot:blocked:{bot_id}')],
        [('🗑 O‘chirish', f'sbot:delete:{bot_id}')],
        [('ℹ️ Batafsil', f'sbot:info:{bot_id}')],
    ]
    return inline(rows)


def payment_actions(payment_id: int):
    return inline([[('✅ Tasdiqlash', f'pay:ok:{payment_id}'), ('❌ Rad etish', f'pay:no:{payment_id}')]])
