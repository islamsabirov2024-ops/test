from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def rkb(rows):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=x) for x in row] for row in rows], resize_keyboard=True)


def main_menu():
    return rkb([
        ['➕ Bot yaratish','🤖 Botlarim'],
        ['🗣 Referal','📱 Shaxsiy kabinet'],
        ['🚀 Saytga kirish','💳 Hisob to\'ldirish'],
        ['📩 Murojaat','📚 Qo\'llanma'],
    ])


def bot_types_menu():
    return rkb([
        ['🎬 Kino Bot'],
        ['🚀 Nakrutka Bot'],
        ['💵 Pul Bot'],
        ['📥 OpenBudget Bot'],
        ['🛍 Mahsulot Bot'],
        ['🔐 VipKanal Bot'],
        ['🚀 Smm Bot [💎 PREMIUM]'],
        ['🎥 ProKino Bot [💎 PREMIUM]'],
        ['◀️ Orqaga'],
    ])


def create_kino_menu(price=0):
    rows=[]
    rows.append([f'✅ Bot yaratish — {price:,} so\'m'.replace(',', ' ')])
    rows.append(['📋 Tariflar ro\'yxati'])
    rows.append(['◀️ Orqaga'])
    return rkb(rows)


def super_menu():
    return rkb([
        ['📊 Umumiy statistika','📩 Xabar yuborish'],
        ['🤖 Barcha botlar','💳 To\'lovlar'],
        ['⚙️ Global sozlamalar','👥 Foydalanuvchilar'],
        ['◀️ Orqaga'],
    ])


def global_settings_menu():
    return rkb([
        ['💰 Bot yaratish narxi','🎁 Referal bonus summasi'],
        ['📋 Hozirgi sozlamalar'],
        ['◀️ Orqaga'],
    ])


def topup_menu():
    return rkb([
        ['⚪ Payme (Avto)'],
        ['🔵 Click (Avto)'],
        ['💳 Karta (Avto)'],
        ['💳 Humo'],
        ['◀️ Orqaga'],
    ])


def kino_user_menu(is_admin=False):
    rows=[['💎 Premium','🔍 Kino qidiruv'], ['🆕 Yangi kinolar','🔥 TOP kinolar'], ['❤️ Sevimlilar','📥 Kino so‘rov qilish'], ['🎬 Kino kodi yuborish','🧾 Chek statusi']]
    if is_admin: rows.append(['⚙️ Boshqaruv'])
    return rkb(rows)


def kino_admin_menu():
    return rkb([
        ['📊 Statistika','📩 Xabar yuborish'],
        ['🎬 Kontent boshqaruvi','🔐 Kanallar'],
        ['⚙️ Tizim sozlamalari','📥 So‘rovlar'],
        ['👮 Admin log','👥 Foydalanuvchilar'],
        ['◀️ Orqaga'],
    ])

def content_menu():
    return rkb([
        ['📥 Kino yuklash'],
        ['📝 Kino tahrirlash','🗑 Kino o‘chirish'],
        ['📋 Kinolar ro‘yxati'],
        ['🆕 Yangi kinolar','🔥 TOP kinolar'],
        ['◀️ Orqaga'],
    ])

def settings_menu():
    return rkb([
        ['📢 Reklama','👮 Adminlar'],
        ['↗️ Ulashish','📝 Matnlar'],
        ['💳 To‘lov tizimlari','⚙️ Premium'],
        ['🛡 Anti-spam','🔐 Obuna statistikasi'],
        ['◀️ Asosiy panel'],
    ])

def premium_admin_menu():
    return rkb([
        ['💡 Holat o‘zgartirish'],
        ['👥 Premium foydalanuvchilar ro‘yxati'],
        ['📋 Premium tariflar'],
        ['➕ Premium berish / Muddatni boshqarish'],
        ['➖ Premium olib tashlash'],
        ['◀️ Asosiy panel'],
    ])

def pay_menu():
    return rkb([
        ['⚡ Avtomatik to‘lov tizimlari'],
        ['📝 Oddiy to‘lov tizimlari'],
        ['📋 To‘lov tizimlari ro‘yxati'],
        ['➕ To‘lov tizimi qo‘shish'],
        ['◀️ Asosiy panel'],
    ])

def ads_menu():
    return rkb([
        ['🚀 Start: almashtirish','🎬 Kino: almashtirish'],
        ['➕ Reklama qo‘shish','📅 Reklama rejalash'],
        ['📋 Reklamalar ro‘yxati','📢 Reklama preview'],
        ['◀️ Asosiy panel'],
    ])

def admins_menu():
    return rkb([
        ['➕ Admin qo‘shish','➖ Adminni o‘chirish'],
        ['📋 Adminlar ro‘yxati'],
        ['◀️ Asosiy panel'],
    ])

def protect_menu():
    return rkb([
        ['👥 Oddiy (🔒 Ruxsat berish)'],
        ['🌟 Premium (🔒 Ruxsat berish)'],
        ['◀️ Asosiy panel'],
    ])

def texts_menu():
    return rkb([
        ['👋 Start xabari'], ['📢 Kanallar chiqadigan matn'], ['➕ Obuna bo‘lish tugmasi'], ['✅ Tekshirish tugmasi'],
        ['🎬 Kino caption matni'], ['↗️ Ulashish tugmasi'], ['🔒 Premium kino xabari'], ['💎 Premium tugmasi'],
        ['🎬 Kino qismlari sarlavhasi'], ['❌ Noto‘g‘ri kod xabari'], ['💳 Qism nomi matni'], ['🎬 Kino nomi matni'], ['◀️ Asosiy panel'],
    ])

def channels_menu():
    return rkb([
        ['➕ Kanal qo‘shish'], ['📋 Ro‘yxatni ko‘rish'], ['🗑 Kanalni o‘chirish'], ['🔐 Obuna statistikasi'], ['◀️ Orqaga'],
    ])

def antispam_menu():
    return rkb([
        ['🛡 Anti-spam ON/OFF'], ['⚡ Limit sozlash'], ['⏱ Blok vaqtini sozlash'], ['◀️ Asosiy panel'],
    ])

def bot_actions(bot_id:int, status='active'):
    b=InlineKeyboardBuilder(); b.button(text='🟢 Yoqish' if status!='active' else '🔴 To‘xtatish', callback_data=f'bot_toggle:{bot_id}'); b.button(text='🔑 Token almashtirish', callback_data=f'bot_token:{bot_id}'); b.button(text='🗑 O‘chirish', callback_data=f'bot_delete:{bot_id}'); b.adjust(1); return b.as_markup()

def sub_check():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tekshirish', callback_data='check_sub')]])

def tariff_inline(rows):
    b=InlineKeyboardBuilder()
    for r in rows: b.button(text=f"💎 {r['name']} — {r['days']} kun — {r['price']:,} so‘m".replace(',', ' '), callback_data=f'buy_tariff:{r["id"]}')
    b.adjust(1); return b.as_markup()

def pay_methods_inline(rows, tariff_id):
    b=InlineKeyboardBuilder()
    for r in rows: b.button(text=f"💳 {r['name']}", callback_data=f'pay_method:{tariff_id}:{r["id"]}')
    b.adjust(1); return b.as_markup()

def payment_admin_inline(payment_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tasdiqlash', callback_data=f'pay_ok:{payment_id}'), InlineKeyboardButton(text='❌ Rad etish', callback_data=f'pay_no:{payment_id}')]])

def movie_inline(movie_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❤️ Sevimlilarga qo‘shish/olish', callback_data=f'fav:{movie_id}')]])

def request_admin_inline(req_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Bajarildi', callback_data=f'req_done:{req_id}'), InlineKeyboardButton(text='❌ Rad', callback_data=f'req_no:{req_id}')]])
