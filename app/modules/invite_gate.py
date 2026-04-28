from __future__ import annotations
from aiogram import Dispatcher, F
from aiogram.types import Message
from app.db import inc_join
def setup(dp:Dispatcher, bot_id:int, owner_id:int):
    @dp.message(F.text=='/start')
    async def start(m:Message): await m.answer('👥 Invite bot ishlayapti. Guruhga qo‘shing, yangi a’zolarni sanaydi va salom beradi.')
    @dp.message(F.new_chat_members)
    async def new_members(m:Message):
        for u in m.new_chat_members:
            await inc_join(bot_id,m.chat.id,u.id)
            await m.answer(f'👋 Xush kelibsiz, {u.full_name}!')
