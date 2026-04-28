from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BACK = '⬅️ Orqaga'
CANCEL = '❌ Bekor qilish'

TARIFFS = {
    'start': {'title': '🚀 Start', 'price': 18000, 'days': 30, 'users': '0-1000 obunachi'},
    'standard': {'title': '⚡ Standard', 'price': 35000, 'days': 30, 'users': '1000-5000 obunachi'},
    'pro': {'title': '💎 Pro', 'price': 90000, 'days': 30, 'users': '5000-20000 obunachi'},
    'vip': {'title': '👑 VIP', 'price': 200000, 'days': 30, 'users': 'Cheksiz / VIP'},
}

def money(n: int) -> str:
    return f'{int(n):,}'.replace(',', ' ')

def main_menu(is_admin: bool = False):
    rows = [
        [KeyboardButton(text='➕ Bot yaratish'), KeyboardButton(text='🤖 Botlarim')],
        [KeyboardButton(text='💳 Tariflar'), KeyboardButton(text='👤 Kabinet')],
        [KeyboardButton(text='📞 Support')],
    ]
    if is_admin:
        rows.append([KeyboardButton(text='🧾 To‘lovlar'), KeyboardButton(text='📊 Admin statistika')])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def back_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BACK)]], resize_keyboard=True)

def cancel_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CANCEL)]], resize_keyboard=True)

def bot_types():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎬 Kino bot', callback_data='type:movie')],
        [InlineKeyboardButton(text='🧹 Reklama tozalovchi bot', callback_data='type:ad_cleaner')],
        [InlineKeyboardButton(text='🎵 Qo‘shiq topuvchi bot', callback_data='type:music_finder')],
        [InlineKeyboardButton(text='👥 Odam qo‘shib yozish bot', callback_data='type:invite_gate')],
        [InlineKeyboardButton(text='💻 IT darslik bot', callback_data='type:it_lessons')],
        [InlineKeyboardButton(text='📥 Yuklovchi bot', callback_data='type:downloader')],
    ])

def tariff_kb(bot_id: int):
    rows = [[InlineKeyboardButton(text=f'{v["title"]} — {money(v["price"])} so‘m', callback_data=f'tariff:{bot_id}:{k}')] for k, v in TARIFFS.items()]
    rows.append([InlineKeyboardButton(text='⬅️ Orqaga', callback_data='menu:back')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def pay_kb(bot_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📸 Chek yuborish', callback_data=f'pay:{bot_id}')],
        [InlineKeyboardButton(text='⬅️ Orqaga', callback_data='menu:back')],
    ])

def pay_admin(pid: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='✅ Tasdiqlash', callback_data=f'payok:{pid}'),
        InlineKeyboardButton(text='❌ Rad etish', callback_data=f'payno:{pid}'),
    ]])

def manage_bot(bot_id: int, active: bool):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚙️ Boshqarish', callback_data=f'open:{bot_id}')],
        [InlineKeyboardButton(text='▶️ Yoqish', callback_data=f'run:{bot_id}'), InlineKeyboardButton(text='⏸ O‘chirish', callback_data=f'stop:{bot_id}')],
        [InlineKeyboardButton(text='🔑 Token yangilash', callback_data=f'token:{bot_id}')],
        [InlineKeyboardButton(text='💳 Tarif/To‘lov', callback_data=f'tariffs:{bot_id}'), InlineKeyboardButton(text='🗑 O‘chirish', callback_data=f'delete:{bot_id}')],
    ])

def delete_confirm(bot_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='✅ Ha, o‘chir', callback_data=f'delok:{bot_id}'),
        InlineKeyboardButton(text='❌ Yo‘q', callback_data=f'open:{bot_id}'),
    ]])

def cleaner_settings_kb(s: dict):
    def mark(k):
        return '✅' if s.get(k, 1) else '❌'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f'{mark("links")} Ssilka', callback_data='cl:t:links'), InlineKeyboardButton(text=f'{mark("mentions")} @kanal', callback_data='cl:t:mentions')],
        [InlineKeyboardButton(text=f'{mark("forward")} Forward', callback_data='cl:t:forward'), InlineKeyboardButton(text=f'{mark("buttons")} URL tugma', callback_data='cl:t:buttons')],
        [InlineKeyboardButton(text=f'{mark("words")} Spam so‘z', callback_data='cl:t:words'), InlineKeyboardButton(text=f'{mark("ban")} Warn/Ban', callback_data='cl:t:ban')],
    ])

def search_buttons(q: str):
    import urllib.parse
    x = urllib.parse.quote(q)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='▶️ YouTube', url=f'https://www.youtube.com/results?search_query={x}')],
        [InlineKeyboardButton(text='🔎 Google', url=f'https://www.google.com/search?q={x}')],
    ])

# ===== CLEANER MENU =====
def cleaner_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🟢 Status'), KeyboardButton(text='⚙️ Sozlamalar')],
            [KeyboardButton(text='🚫 Blacklist'), KeyboardButton(text='✅ Whitelist')],
            [KeyboardButton(text='🧪 Test'), KeyboardButton(text='📜 Log')],
            [KeyboardButton(text='🧹 Kesh tozalash'), KeyboardButton(text='📘 Qo‘llanma')],
            [KeyboardButton(text=BACK)],
        ],
        resize_keyboard=True,
    )

# ===== IT MENU =====
def it_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🐍 Python'), KeyboardButton(text='🤖 Telegram bot')],
            [KeyboardButton(text='🌐 Web'), KeyboardButton(text='💾 Database')],
            [KeyboardButton(text='🚀 Deploy'), KeyboardButton(text='🧠 Yo‘l xarita')],
            [KeyboardButton(text=BACK)],
        ],
        resize_keyboard=True,
    )

# Backward-compatible aliases for older modules
def ad_cleaner_menu():
    return cleaner_menu()

def invite_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='🟢 Status'), KeyboardButton(text='📊 Statistika')],
            [KeyboardButton(text='📘 Qo‘llanma'), KeyboardButton(text=BACK)],
        ],
        resize_keyboard=True,
    )
