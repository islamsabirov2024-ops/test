from __future__ import annotations
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from app import db

CATS={'python':'🐍 Python','bot':'🤖 Telegram bot','web':'🌐 Web','db':'💾 Database','deploy':'🚀 Deploy'}
ADMIN_CMDS={'➕ Dars qo‘shish','📚 Darslar','💰 Pullik darslar','📊 Statistika','⬅️ Orqaga'}

def menu(owner=False):
    rows=[[KeyboardButton(text='🐍 Python'),KeyboardButton(text='🤖 Telegram bot')],[KeyboardButton(text='🌐 Web'),KeyboardButton(text='💾 Database')],[KeyboardButton(text='🚀 Deploy'),KeyboardButton(text='🧠 Yo‘l xarita')]]
    if owner: rows.append([KeyboardButton(text='➕ Dars qo‘shish'),KeyboardButton(text='📚 Darslar')])
    return ReplyKeyboardMarkup(keyboard=rows,resize_keyboard=True)

def lesson_kb(bid:int, lessons):
    rows=[]
    for l in lessons:
        price=int(l['price'] or 0); mark='🆓' if price==0 else f'💳 {price} so‘m'
        rows.append([InlineKeyboardButton(text=f'{mark} {l["title"]}', callback_data=f'it:open:{l["id"]}')])
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text='📭 Dars yo‘q',callback_data='it:none')]])

def setup(dp:Dispatcher,bid:int,owner:int):
    async def start(m:Message):
        await db.seed_default_lessons(bid)
        is_owner=m.from_user.id==owner
        await m.answer('💻 <b>IT darslik bot</b>\n\n<blockquote>1-darslar bepul. Keyingi darslarni admin pullik/bepul qilib qo‘yishi mumkin.</blockquote>',reply_markup=menu(is_owner))

    async def category(m:Message):
        await db.seed_default_lessons(bid)
        key=None
        for k,v in CATS.items():
            if m.text.startswith(v.split()[0]) or m.text==v: key=k
        if not key and m.text=='🧠 Yo‘l xarita':
            await m.answer('🧠 <b>0 dan PRO gacha yo‘l</b>\n\n<blockquote>1) Python asoslari\n2) Telegram bot\n3) Database\n4) Web/API\n5) Deploy\n6) Portfolio va mijoz topish</blockquote>',reply_markup=menu(m.from_user.id==owner)); return
        lessons=await db.list_lessons(bid,key)
        await m.answer(f'{CATS.get(key,"📚 Darslar")} bo‘limi:',reply_markup=lesson_kb(bid,lessons))

    async def add_lesson_start(m:Message):
        if m.from_user.id!=owner: return
        await m.answer('➕ Dars qo‘shish formati:\n<blockquote>kategoriya|narx|sarlavha|matn\npython|0|1-dars|Dars matni...</blockquote>')

    async def add_lesson_parse(m:Message):
        if m.from_user.id!=owner: return False
        text=m.text or ''
        if '|' not in text: return False
        parts=text.split('|',3)
        if len(parts)<4 or parts[0] not in CATS: return False
        cat,price,title,body=parts
        await db.add_lesson(bid,cat,title,body,'',int(price or 0))
        await m.answer('✅ Dars qo‘shildi.',reply_markup=menu(True))
        return True

    async def open_lesson(c:CallbackQuery):
        lid=int(c.data.split(':')[2]); l=await db.get_lesson(bid,lid)
        if not l: await c.answer('Topilmadi',show_alert=True); return
        price=int(l['price'] or 0)
        bought=await db.has_lesson(bid,lid,c.from_user.id)
        if price>0 and c.from_user.id!=owner and not bought:
            await c.message.answer(f'🔒 <b>Pullik dars</b>\n\n<blockquote>{l["title"]}\nNarx: {price} so‘m</blockquote>\n\nBu darsni sotib olish uchun bot egasiga to‘lov qiling.', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Admin tasdiqladi deb ochish',callback_data=f'it:buy:{lid}')]]))
            await c.answer(); return
        txt=f'📘 <b>{l["title"]}</b>\n\n<blockquote>{l["body"]}</blockquote>'
        if l['image_file_id']:
            await c.message.answer_photo(l['image_file_id'],caption=txt)
        else:
            await c.message.answer(txt)
        await c.answer()

    async def buy(c:CallbackQuery):
        lid=int(c.data.split(':')[2])
        # Manual model: real to‘lovni bot egasi ko‘rib tasdiqlashi mumkin. Bu tugma test/demo uchun ochadi.
        await db.buy_lesson(bid,lid,c.from_user.id)
        await c.message.answer('✅ Dars ochildi. Endi qayta bosing.'); await c.answer()

    dp.message.register(start,F.text=='/start')
    dp.message.register(add_lesson_start,F.text=='➕ Dars qo‘shish')
    dp.message.register(category,F.text.in_(set(CATS.values())|{'🧠 Yo‘l xarita','📚 Darslar'}))
    dp.message.register(add_lesson_parse)
    dp.callback_query.register(open_lesson,F.data.startswith('it:open:'))
    dp.callback_query.register(buy,F.data.startswith('it:buy:'))
