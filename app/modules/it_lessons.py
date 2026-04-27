from __future__ import annotations
from aiogram import Dispatcher, F
from aiogram.types import Message
from app.keyboards.common import it_menu
LESSONS={
 '🐍 Python':'🐍 <b>Python 0 dan</b>\n<blockquote>1) print/input\n2) if/for/while\n3) list/dict\n4) async\n5) loyiha: Telegram bot</blockquote>',
 '🤖 Telegram bot':'🤖 <b>Telegram bot darslari</b>\n<blockquote>BotFather, token, aiogram, handler, keyboard, deploy.</blockquote>',
 '🌐 Web':'🌐 <b>Web</b>\n<blockquote>HTML, CSS, JS, FastAPI, API.</blockquote>',
 '💾 Database':'💾 <b>Database</b>\n<blockquote>SQLite, PostgreSQL, jadval, CRUD.</blockquote>',
 '🚀 Deploy':'🚀 <b>Deploy</b>\n<blockquote>Render, Railway, VPS, Docker, ENV.</blockquote>',
 '🧠 Pro maslahat':'🧠 <b>Pro yo‘l</b>\n<blockquote>Har kuni 2 soat: nazariya + amaliy loyiha + GitHub.</blockquote>'}
def setup(dp:Dispatcher, bot_id:int, owner_id:int):
    @dp.message(F.text=='/start')
    async def start(m:Message): await m.answer('💻 <b>IT darslik bot</b>\n<blockquote>0 dan professional darajagacha bo‘lim tanlang.</blockquote>',reply_markup=it_menu())
    @dp.message(F.text.in_(set(LESSONS)))
    async def lesson(m:Message): await m.answer(LESSONS[m.text],reply_markup=it_menu())
    @dp.message()
    async def anymsg(m:Message): await m.answer('👇 Bo‘lim tanlang.',reply_markup=it_menu())
