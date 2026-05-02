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

def super_menu():
    return rkb([
        ['📊 Umumiy statistika','📩 Xabar yuborish'],
        ['🤖 Barcha botlar','💳 To\'lovlar'],
        ['⚙️ Global sozlamalar','👥 Foydalanuvchilar'],
        ['◀️ Orqaga'],
    ])

def kino_admin_menu():
    return rkb([
        ['📊 Statistika','📩 Xabar yuborish'],
        ['🎬 Kontent boshqaruvi','🔐 Kanallar'],
        ['⚙️ Tizim sozlamalari','📥 So‘rovlar'],
        ['◀️ Orqaga','👥 Foydalanuvchilar'],
    ])

def content_menu():
    return rkb([
        ['📥 Kino yuklash'],
        ['📝 Kino tahrirlash','🗑 Kino o‘chirish'],
        ['📋 Kinolar ro‘yxati'],
        ['◀️ Orqaga'],
    ])

def channels_menu():
    return rkb([
        ['➕ Kanal qo‘shish'],
        ['📋 Ro‘yxatni ko‘rish'],
        ['🗑 Kanalni o‘chirish'],
        ['◀️ Orqaga'],
    ])

def settings_menu():
    return rkb([
        ['📢 Reklama','👮 Adminlar'],
        ['↗️ Ulashish','📝 Matnlar'],
        ['💳 To‘lov tizimlari','⚙️ Premium'],
        ['◀️ Asosiy panel'],
    ])

def bot_actions(bot_id:int, status='active'):
    b=InlineKeyboardBuilder()
    b.button(text='🟢 Yoqish' if status!='active' else '🔴 To‘xtatish', callback_data=f'bot_toggle:{bot_id}')
    b.button(text='🔑 Token almashtirish', callback_data=f'bot_token:{bot_id}')
    b.button(text='🗑 O‘chirish', callback_data=f'bot_delete:{bot_id}')
    b.adjust(1)
    return b.as_markup()

def sub_check():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Tekshirish', callback_data='check_sub')]])
