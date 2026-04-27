from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from app.db import inc_join
from app.keyboards.common import invite_menu


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            '👥 <b>Invite bot tayyor!</b>\n\n'
            '<blockquote>Meni guruhga qo‘shing. Yangi kirgan odamlarni sanayman va salom beraman.</blockquote>',
            reply_markup=invite_menu(),
        )

    @r.message(Command('help'))
    async def help_cmd(m: Message):
        await m.answer(
            '📌 <b>Qo‘llanma</b>\n\n'
            '<blockquote>Bot guruhga qo‘shilgandan keyin har bir yangi a’zoni kutib oladi va bazaga sanab boradi.</blockquote>',
            reply_markup=invite_menu(),
        )

    @r.callback_query(F.data.startswith('inv:'))
    async def inv_cb(c: CallbackQuery):
        if c.data == 'inv:stats':
            await c.message.answer('📊 <b>Statistika</b>\n\n<blockquote>Yangi a’zolar bazaga yozib boriladi. Keyingi versiyada guruh bo‘yicha jadval chiqariladi.</blockquote>')
        elif c.data == 'inv:help':
            await c.message.answer('📌 <b>Qo‘llanma</b>\n\n<blockquote>Botni guruhga qo‘shing. Yangi kirganlarga avtomatik salom beradi.</blockquote>')
        else:
            await c.message.answer('👥 Invite bot menyusi', reply_markup=invite_menu())
        await c.answer()

    @r.message(F.new_chat_members)
    async def joined(m: Message):
        for u in m.new_chat_members:
            await inc_join(bot_id, m.chat.id, u.id)
            await m.answer(f'👋 Xush kelibsiz, {u.mention_html()}!')

    dp.include_router(r)
