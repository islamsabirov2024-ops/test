from __future__ import annotations
from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

LESSONS = {
    'zero': {
        'title': '🧱 0-dars: Kompyuter va internet asoslari',
        'body': 'Kompyuter fayl/papka, brauzer, Google, Telegram, ZIP, CMD/Terminal, xavfsizlik va parol asoslari.',
        'steps': ['Fayl va papka yaratish', 'ZIP ochish/yig‘ish', 'CMD ochish', 'Internet xavfsizligi'],
    },
    'python': {
        'title': '🐍 Python 0 dan',
        'body': 'Python o‘rnatish, print, o‘zgaruvchi, if/else, for/while, function, file bilan ishlash.',
        'steps': ['Python 3.11 o‘rnatish', 'VS Code sozlash', 'Birinchi kod', 'Mini loyiha'],
    },
    'telegram': {
        'title': '🤖 Telegram bot yaratish',
        'body': 'BotFather, token, aiogram, command, message handler, inline/reply keyboard, deploy.',
        'steps': ['BotFather token', 'aiogram start', 'knopkalar', 'Render/Railway deploy'],
    },
    'web': {
        'title': '🌐 Web dasturlash',
        'body': 'HTML, CSS, JavaScript, responsive dizayn, GitHub Pages va oddiy landing page.',
        'steps': ['HTML strukturasi', 'CSS dizayn', 'JS interaktivlik', 'Sayt chiqarish'],
    },
    'db': {
        'title': '🗄 Database',
        'body': 'SQLite/PostgreSQL, jadval, insert/select/update/delete, backup va migratsiya.',
        'steps': ['Jadval yaratish', 'Ma’lumot qo‘shish', 'Qidirish', 'Railway Postgres'],
    },
    'deploy': {
        'title': '🚀 Deploy va server',
        'body': 'Render, Railway, Hetzner VPS, environment variables, logs, restart, monitoring.',
        'steps': ['requirements.txt', 'Start command', 'ENV qo‘yish', 'Log o‘qish'],
    },
    'pro': {
        'title': '💼 Professional daraja',
        'body': 'Arxitektura, security, payment, SaaS, multi-bot, webhook, scaling, monitoring.',
        'steps': ['Kod tuzilmasi', 'Xavfsizlik', 'To‘lov tizimi', 'Katta trafik'],
    },
}


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🧱 0 dan boshlash', callback_data='it:zero')],
        [InlineKeyboardButton(text='🐍 Python', callback_data='it:python'), InlineKeyboardButton(text='🤖 Telegram bot', callback_data='it:telegram')],
        [InlineKeyboardButton(text='🌐 Web', callback_data='it:web'), InlineKeyboardButton(text='🗄 Database', callback_data='it:db')],
        [InlineKeyboardButton(text='🚀 Deploy', callback_data='it:deploy'), InlineKeyboardButton(text='💼 Pro daraja', callback_data='it:pro')],
        [InlineKeyboardButton(text='🖼 Rasmlar bilan yo‘riqnoma', callback_data='it:pictures')],
    ])


def lesson_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='📌 Keyingi mavzular', callback_data='it:menu')],
        [InlineKeyboardButton(text='🧪 Amaliy vazifa', callback_data='it:task')],
    ])


def lesson_text(code: str) -> str:
    l = LESSONS[code]
    steps = '\n'.join([f'{i+1}. {x}' for i, x in enumerate(l['steps'])])
    return (
        f'{l["title"]}\n\n'
        f'<blockquote>{l["body"]}</blockquote>\n\n'
        f'📋 <b>Dars rejasi:</b>\n{steps}\n\n'
        '🖼 Rasmli tushuntirish: har qadamni skrinshot bilan ko‘rish uchun “Rasmlar bilan yo‘riqnoma” bo‘limiga kiring.'
    )


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            '💻 <b>IT Darslik Bot</b>\n\n'
            '<blockquote>Bu bot IT ni 0 dan professional darajagacha bosqichma-bosqich o‘rgatadi: Python, Telegram bot, Web, Database, Deploy va SaaS.</blockquote>\n\n'
            '👇 Kerakli bo‘limni tanlang.',
            reply_markup=main_kb(),
        )

    @r.message(Command('help'))
    async def help_cmd(m: Message):
        await start(m)

    @r.callback_query(F.data == 'it:menu')
    async def menu(c: CallbackQuery):
        await c.message.answer('📚 <b>Dars bo‘limlari</b>', reply_markup=main_kb())
        await c.answer()

    @r.callback_query(F.data.startswith('it:'))
    async def open_lesson(c: CallbackQuery):
        code = c.data.split(':', 1)[1]
        if code in LESSONS:
            await c.message.answer(lesson_text(code), reply_markup=lesson_kb())
        elif code == 'pictures':
            await c.message.answer(
                '🖼 <b>Rasmlar bilan yo‘riqnoma</b>\n\n'
                '<blockquote>Bu bo‘limda har bir mavzu rasm/skrinshot bilan tushuntiriladi. Hozir matnli rasm-o‘rinbosarlar tayyor: deployda haqiqiy rasm URL yoki Telegram file_id qo‘shsangiz avtomatik rasm yuboradi.</blockquote>\n\n'
                '1️⃣ Python o‘rnatish oynasi\n'
                '2️⃣ VS Code ochilishi\n'
                '3️⃣ Terminalda komandalar\n'
                '4️⃣ BotFather token olish\n'
                '5️⃣ Render/Railway deploy sozlamalari',
                reply_markup=lesson_kb(),
            )
        elif code == 'task':
            await c.message.answer(
                '🧪 <b>Amaliy vazifa</b>\n\n'
                '<blockquote>Bugungi vazifa: /start bosilganda salom beradigan Telegram bot yozing, keyin unga 2 ta tugma qo‘shing.</blockquote>\n\n'
                '✅ Tugmalar: “📚 Darslar” va “📞 Support”'
            )
        await c.answer()

    @r.message()
    async def any_msg(m: Message):
        await m.answer('💻 Darslik menyusini ochish uchun /start bosing.', reply_markup=main_kb())

    dp.include_router(r)
