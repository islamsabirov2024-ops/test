from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

BACK = '◀️ Orqaga'
CANCEL = '❌ Bekor qilish'

TARIFFS = {
    'start': {'title':'🚀 Start', 'price':9000, 'per_day':300, 'users':'1 000 ta', 'speed':'~0.3s'},
    'standard': {'title':'✅⭐ Standard', 'price':18000, 'per_day':600, 'users':'13 / 1 000', 'speed':'~0.2s'},
    'pro': {'title':'💎 Pro', 'price':35000, 'per_day':1167, 'users':'5 000 ta', 'speed':'~0.15s'},
    'turbo': {'title':'⚡ Turbo', 'price':65000, 'per_day':2167, 'users':'10 000 ta', 'speed':'~0.1s'},
    'ultra': {'title':'🔥 Ultra', 'price':90000, 'per_day':3000, 'users':'15 000 ta', 'speed':'~0.1s'},
    'unlimited': {'title':'∞ Unlimited', 'price':150000, 'per_day':5000, 'users':'Cheksiz', 'speed':'~0s'},
}
DURATIONS = [1,3,7,10,20,30]

def money(n:int)->str:
    return f"{n:,}".replace(',', ' ')

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='➕ Bot yaratish'), KeyboardButton(text='🤖 Botlarim')],
            [KeyboardButton(text='🫂 Referal'), KeyboardButton(text='🧾 Shaxsiy kabinet')],
            [KeyboardButton(text='🚀 Saytga kirish'), KeyboardButton(text="💳 Hisob to'ldirish")],
            [KeyboardButton(text='📨 Murojaat'), KeyboardButton(text="📚 Qo'llanma")],
        ],
        resize_keyboard=True,
        input_field_placeholder='Menu'
    )

def back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BACK)]], resize_keyboard=True, input_field_placeholder='Orqaga')

def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=CANCEL)], [KeyboardButton(text=BACK)]], resize_keyboard=True)

def bot_types() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎬 Kino bot', callback_data='type:movie')],
        [InlineKeyboardButton(text='🧹 Reklama tozalovchi bot', callback_data='type:ad_cleaner')],
        [InlineKeyboardButton(text="🎵 Qo'shiq topuvchi bot", callback_data='type:music_finder')],
        [InlineKeyboardButton(text="👥 Odam qo'shib yozish bot", callback_data='type:invite_gate')],
        [InlineKeyboardButton(text="💻 IT darslik bot", callback_data="type:it_lessons")],
        [InlineKeyboardButton(text=BACK, callback_data='menu:back')],
    ])

def bots_list_kb(bots) -> InlineKeyboardMarkup:
    rows=[]
    for b in bots:
        rows.append([InlineKeyboardButton(text=f'⚙️ @{b["bot_username"] or b["bot_name"]}', callback_data=f'bot:{b["id"]}')])
    rows.append([InlineKeyboardButton(text=BACK, callback_data='menu:back')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def manage_bot(bot_id: int, active: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='⚙️ Botni sozlash', callback_data=f'settings:{bot_id}')],
        [InlineKeyboardButton(text="📊 Tarifni o'zgartirish", callback_data=f'tariff:{bot_id}')],
        [InlineKeyboardButton(text="💵 To'lov Muddati", callback_data=f'paydays:{bot_id}')],
        [InlineKeyboardButton(text='📈 Dashboard (Web)', callback_data=f'dashboard:{bot_id}')],
        [InlineKeyboardButton(text=BACK, callback_data='menu:my_bots'), InlineKeyboardButton(text="🗑 O'chirish", callback_data=f'delete:{bot_id}')],
    ])

def settings_bot_kb(bot_id:int, active: bool=False) -> InlineKeyboardMarkup:
    run_text = '🔄 Botni Yangilash' if active else '▶️ Botni Ishga tushirish'
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔑 Tokenni Yangilash', callback_data=f'newtoken:{bot_id}'), InlineKeyboardButton(text=run_text, callback_data=f'run:{bot_id}')],
        [InlineKeyboardButton(text="🔀 Botni O'tkazish", callback_data=f'transfer:{bot_id}'), InlineKeyboardButton(text='🆔 Admin ID', callback_data=f'adminid:{bot_id}')],
        [InlineKeyboardButton(text='🧹 Keshni Tozalash', callback_data=f'clearcache:{bot_id}')],
        [InlineKeyboardButton(text=BACK, callback_data=f'bot:{bot_id}')],
    ])

def tariff_select_kb(bot_id:int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🚀 Start — 9 000 so‘m', callback_data=f'settariff:{bot_id}:start')],
        [InlineKeyboardButton(text='✅⭐ Standard — 18 000 so‘m', callback_data=f'settariff:{bot_id}:standard')],
        [InlineKeyboardButton(text='💎 Pro — 35 000 so‘m 🔥', callback_data=f'settariff:{bot_id}:pro')],
        [InlineKeyboardButton(text='⚡ Turbo — 65 000 so‘m', callback_data=f'settariff:{bot_id}:turbo')],
        [InlineKeyboardButton(text='🔥 Ultra — 90 000 so‘m', callback_data=f'settariff:{bot_id}:ultra')],
        [InlineKeyboardButton(text='∞ Unlimited — 150 000 so‘m', callback_data=f'settariff:{bot_id}:unlimited')],
        [InlineKeyboardButton(text=BACK, callback_data=f'bot:{bot_id}')],
    ])

def duration_kb(bot_id:int, tariff:str) -> InlineKeyboardMarkup:
    t=TARIFFS.get(tariff, TARIFFS['standard'])
    rows=[]
    for d in DURATIONS:
        rows.append([InlineKeyboardButton(text=f'{d} kun — {money(t["per_day"]*d)} so‘m', callback_data=f'pay:{bot_id}:{tariff}:{d}')])
    rows.append([InlineKeyboardButton(text=BACK, callback_data=f'tariff:{bot_id}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def delete_confirm(bot_id:int)->InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f'delok:{bot_id}')],
        [InlineKeyboardButton(text=BACK, callback_data=f'bot:{bot_id}')],
    ])

# Kino bot ichki admin paneli
# Render xatosi uchun qo'shildi: movie.py shu funksiyani import qiladi.
def movie_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🎬 Kino qo‘shish', callback_data='m:add')],
        [InlineKeyboardButton(text='📋 Kinolar ro‘yxati', callback_data='m:list')],
        [InlineKeyboardButton(text='🔐 Premium yoqish/o‘chirish', callback_data='m:premium')],
        [InlineKeyboardButton(text='📢 Majburiy obuna', callback_data='m:channels')],
        [InlineKeyboardButton(text='📊 Statistika', callback_data='m:stats')],
        [InlineKeyboardButton(text='📚 Qo‘llanma', callback_data='m:help')],
        [InlineKeyboardButton(text='🗑 Kino o‘chirish', callback_data='m:del')],
        [InlineKeyboardButton(text='◀️ Orqaga', callback_data='m:back')],
    ])
