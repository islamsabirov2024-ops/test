from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def user_main(is_super: bool=False):
    rows = [
        [InlineKeyboardButton('🤖 Bot yaratish', callback_data='create_menu')],
        [InlineKeyboardButton('⚙️ Mening botlarim', callback_data='my_bots')],
        [InlineKeyboardButton('💳 To‘lov qilish', callback_data='pay_menu')],
        [InlineKeyboardButton('📘 Qo‘llanma', callback_data='help')],
    ]
    if is_super:
        rows.insert(0, [InlineKeyboardButton('👑 SUPER ADMIN PANEL', callback_data='super_panel')])
    return InlineKeyboardMarkup(rows)

def create_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🎬 Kino bot yaratish', callback_data='create_type:movie')],
        [InlineKeyboardButton('🧹 Reklama tozalovchi bot', callback_data='create_type:cleaner')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data='home')],
    ])

def super_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🤖 Barcha botlar', callback_data='admin_bots')],
        [InlineKeyboardButton('💳 Cheklar', callback_data='admin_payments')],
        [InlineKeyboardButton('📊 Statistika', callback_data='admin_stats')],
        [InlineKeyboardButton('📨 Xabar yuborish', callback_data='admin_broadcast')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data='home')],
    ])

def bot_owner_actions(bot_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🎛 Bot paneli', callback_data=f'bot_panel:{bot_id}')],
        [InlineKeyboardButton('💳 Karta qo‘shish', callback_data=f'set_card:{bot_id}')],
        [InlineKeyboardButton('💰 Narx sozlash', callback_data=f'set_price:{bot_id}')],
        [InlineKeyboardButton('📸 Chek yuborish', callback_data=f'send_payment:{bot_id}')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data='my_bots')],
    ])

def admin_bot_actions(bot_id:int, running:int, paid:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ To‘lovni tasdiqlash', callback_data=f'admin_paybot:{bot_id}')],
        [InlineKeyboardButton('▶️ Ishga tushirish' if not running else '⏸ To‘xtatish', callback_data=f'admin_togglebot:{bot_id}')],
        [InlineKeyboardButton('🔓 Pullik holat: ON' if paid else '🔒 Pullik holat: OFF', callback_data=f'admin_paybot:{bot_id}')],
        [InlineKeyboardButton('⬅️ Botlar ro‘yxati', callback_data='admin_bots')],
    ])

def payment_actions(payment_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Tasdiqlash', callback_data=f'pay_accept:{payment_id}')],
        [InlineKeyboardButton('❌ Rad etish', callback_data=f'pay_reject:{payment_id}')],
        [InlineKeyboardButton('⬅️ Cheklar', callback_data='admin_payments')],
    ])
