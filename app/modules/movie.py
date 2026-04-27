from aiogram import Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db import add_movie, get_movie, list_movies, delete_movie
from app.keyboards.common import movie_admin, cancel_menu, main_menu

class MovieState(StatesGroup):
    code = State()
    title = State()
    post = State()
    del_code = State()


def parse_post_ref(m: Message):
    chat_id = None
    msg_id = None

    if getattr(m, 'forward_from_chat', None) and getattr(m, 'forward_from_message_id', None):
        chat_id = str(m.forward_from_chat.id)
        msg_id = m.forward_from_message_id

    origin = getattr(m, 'forward_origin', None)
    if origin and not chat_id:
        try:
            if getattr(origin, 'chat', None) and getattr(origin, 'message_id', None):
                chat_id = str(origin.chat.id)
                msg_id = origin.message_id
        except Exception:
            pass

    text = (m.text or '').strip()
    if not chat_id and ('t.me/' in text or 'telegram.me/' in text):
        try:
            clean = text.split('?')[0].rstrip('/')
            parts = clean.split('/')
            msg_id = int(parts[-1])
            if '/c/' in clean:
                idx = parts.index('c')
                chat_id = '-100' + parts[idx + 1]
            else:
                username = parts[-2]
                chat_id = '@' + username
        except Exception:
            pass
    return chat_id, msg_id


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            '👋 <b>Assalomu alaykum!</b>\n\n'
            '<blockquote>Kino olish uchun kino kodini yuboring.</blockquote>\n\n'
            'Masalan: <code>123</code>'
        )

    @r.message(Command('admin'))
    async def admin(m: Message):
        if m.from_user.id != owner_id:
            return
        await m.answer('👮 <b>Kino bot admin panel</b>\n\n<blockquote>Kerakli bo‘limni tanlang.</blockquote>', reply_markup=movie_admin())

    @r.callback_query(F.data == 'm:back')
    async def back(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            return
        await state.clear()
        await c.message.answer('👮 Admin panel', reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:add')
    async def add_start(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            return
        await state.set_state(MovieState.code)
        await c.message.answer('🎬 Kino kodini yuboring:\n\nNamuna: <code>avatar1</code>', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.code)
    async def code(m: Message, state: FSMContext):
        if m.from_user.id != owner_id:
            return
        if (m.text or '').strip() in {'⬅️ Orqaga', '❌ Bekor qilish'}:
            await state.clear(); await m.answer('👮 Admin panel', reply_markup=movie_admin()); return
        await state.update_data(code=(m.text or '').strip().lower())
        await state.set_state(MovieState.title)
        await m.answer('📝 Kino nomini yuboring:', reply_markup=cancel_menu())

    @r.message(MovieState.title)
    async def title(m: Message, state: FSMContext):
        if m.from_user.id != owner_id:
            return
        if (m.text or '').strip() in {'⬅️ Orqaga', '❌ Bekor qilish'}:
            await state.clear(); await m.answer('👮 Admin panel', reply_markup=movie_admin()); return
        await state.update_data(title=(m.text or '').strip())
        await state.set_state(MovieState.post)
        await m.answer(
            '📩 Endi kino postini yuboring.\n\n'
            '<blockquote>Kanal postini forward qiling yoki link yuboring: https://t.me/kanal/123</blockquote>\n\n'
            '⚠️ Bot kino kanalida admin bo‘lishi kerak.',
            reply_markup=cancel_menu(),
        )

    @r.message(MovieState.post)
    async def post(m: Message, state: FSMContext):
        if m.from_user.id != owner_id:
            return
        if (m.text or '').strip() in {'⬅️ Orqaga', '❌ Bekor qilish'}:
            await state.clear(); await m.answer('👮 Admin panel', reply_markup=movie_admin()); return
        data = await state.get_data()
        chat_id, msg_id = parse_post_ref(m)
        if not chat_id or not msg_id:
            await m.answer('❌ Post aniqlanmadi. Forward qiling yoki t.me kanal posti linkini yuboring.', reply_markup=cancel_menu())
            return
        await add_movie(bot_id, data['code'], data['title'], chat_id, msg_id)
        await state.clear()
        await m.answer(
            '✅ <b>Kino saqlandi!</b>\n\n'
            f'🎬 Kod: <code>{data["code"]}</code>\n'
            f'📝 Nom: <b>{data["title"]}</b>',
            reply_markup=movie_admin(),
        )

    @r.callback_query(F.data == 'm:list')
    async def movie_list(c: CallbackQuery):
        if c.from_user.id != owner_id:
            return
        rows = await list_movies(bot_id)
        if not rows:
            await c.message.answer('📭 Kino yo‘q.', reply_markup=movie_admin())
            await c.answer(); return
        txt = '📋 <b>Kinolar ro‘yxati</b>\n\n' + '\n'.join([
            f'• <code>{x["code"]}</code> — {x["title"]} 👁 {x["views"]}' for x in rows
        ])
        await c.message.answer(txt, reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:del')
    async def del_start(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            return
        await state.set_state(MovieState.del_code)
        await c.message.answer('🗑 O‘chiriladigan kino kodini yuboring:', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.del_code)
    async def del_code(m: Message, state: FSMContext):
        if m.from_user.id != owner_id:
            return
        if (m.text or '').strip() in {'⬅️ Orqaga', '❌ Bekor qilish'}:
            await state.clear(); await m.answer('👮 Admin panel', reply_markup=movie_admin()); return
        await delete_movie(bot_id, (m.text or '').strip())
        await state.clear()
        await m.answer('✅ Kino o‘chirildi.', reply_markup=movie_admin())

    @r.message(F.text)
    async def by_code(m: Message):
        code = (m.text or '').strip().lower()
        if code.startswith('/'):
            return
        movie = await get_movie(bot_id, code)
        if not movie:
            await m.answer('❌ Bunday kod topilmadi. Kodni tekshirib yuboring.')
            return
        try:
            await m.bot.copy_message(chat_id=m.chat.id, from_chat_id=movie['chat_id'], message_id=movie['message_id'])
        except Exception as e:
            await m.answer('⚠️ Kino yuborilmadi. Botni kino kanaliga admin qiling yoki linkni tekshiring.\n<code>' + str(e)[:200] + '</code>')

    dp.include_router(r)
