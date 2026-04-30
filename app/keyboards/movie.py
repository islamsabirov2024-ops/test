from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def movie_admin(bot_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📊 Statistika', callback_data=f'movie_stats:{bot_id}')],
        [InlineKeyboardButton('🎬 Kontent boshqaruvi', callback_data=f'movie_content:{bot_id}')],
        [InlineKeyboardButton('🔐 Kanallar', callback_data=f'movie_channels:{bot_id}')],
        [InlineKeyboardButton('⚙️ Tizim sozlamalari', callback_data=f'movie_settings:{bot_id}')],
        [InlineKeyboardButton('💳 To‘lov tizimlari', callback_data=f'movie_payments:{bot_id}')],
        [InlineKeyboardButton('💎 Premium', callback_data=f'movie_premium:{bot_id}')],
        [InlineKeyboardButton('📣 Reklama', callback_data=f'movie_ads:{bot_id}')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data='my_bots')],
    ])

def movie_content(bot_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Kino qo‘shish', callback_data=f'add_movie:{bot_id}')],
        [InlineKeyboardButton('📋 Kinolar ro‘yxati', callback_data=f'list_movies:{bot_id}')],
        [InlineKeyboardButton('🗑 Kino o‘chirish', callback_data=f'del_movie_start:{bot_id}')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data=f'bot_panel:{bot_id}')],
    ])

def toggle_menu(bot_id:int, prefix:str, states:dict):
    rows=[]
    labels = {
        'mandatory_sub':'🔐 Majburiy obuna', 'fake_verify':'🧪 Hiyla tekshirish',
        'premium':'💎 Premium', 'ads':'📣 Reklama', 'cleaner_links':'🔗 Link tozalash',
        'cleaner_forwards':'↪️ Forward tozalash', 'cleaner_usernames':'👤 Username tozalash'
    }
    for key,val in states.items():
        rows.append([InlineKeyboardButton(f"{labels.get(key,key)}: {'✅ ON' if val=='on' else '❌ OFF'}", callback_data=f'toggle:{bot_id}:{key}')])
    rows.append([InlineKeyboardButton('⬅️ Orqaga', callback_data=f'bot_panel:{bot_id}')])
    return InlineKeyboardMarkup(rows)

def channels(bot_id:int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('➕ Kanal qo‘shish', callback_data=f'add_channel:{bot_id}')],
        [InlineKeyboardButton('📋 Kanallar ro‘yxati', callback_data=f'list_channels:{bot_id}')],
        [InlineKeyboardButton('🔐 Majburiy obuna sozlash', callback_data=f'movie_settings:{bot_id}')],
        [InlineKeyboardButton('⬅️ Orqaga', callback_data=f'bot_panel:{bot_id}')],
    ])

def subscribe_kb(channels):
    rows=[]
    for c in channels:
        rows.append([InlineKeyboardButton(f"📢 {c['title']}", url=c['link'] or f"https://t.me/{c['username'].lstrip('@')}")])
    rows.append([InlineKeyboardButton('✅ Tekshirish', callback_data='child_check_subs')])
    return InlineKeyboardMarkup(rows)
