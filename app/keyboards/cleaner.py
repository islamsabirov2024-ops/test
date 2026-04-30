from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def cleaner_admin(bot_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('👥 Guruh sozlamalari', callback_data=f'cleaner_groups:{bot_id}')],
        [InlineKeyboardButton('⚙️ Tozalash sozlamalari', callback_data=f'cleaner_settings:{bot_id}')],
        [InlineKeyboardButton('📊 Statistika', callback_data=f'cleaner_stats:{bot_id}')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data='my_bots')],
    ])

def invite_limits(bot_id:int, chat_id:str='default'):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f'👥 {n} odam', callback_data=f'set_invites:{bot_id}:{chat_id}:{n}') for n in (5,10)],
        [InlineKeyboardButton(f'👥 {n} odam', callback_data=f'set_invites:{bot_id}:{chat_id}:{n}') for n in (15,20)],
        [InlineKeyboardButton(f'👥 {n} odam', callback_data=f'set_invites:{bot_id}:{chat_id}:{n}') for n in (25,30)],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data=f'bot_panel:{bot_id}')],
    ])
