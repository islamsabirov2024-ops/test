from __future__ import annotations

import re
from aiogram import Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db import (
    add_movie, get_movie, list_movies, delete_movie, get_settings, save_settings,
    set_movie_premium, increment_movie_views,
)
from app.keyboards.common import movie_admin, movie_admin_reply, cancel_menu, movie_channel_menu

BACK_WORDS = {'⬅️ Orqaga', '◀️ Orqaga', '❌ Bekor qilish'}

class MovieState(StatesGroup):
    code = State()
    title = State()
    post = State()
    del_code = State()
    premium_code = State()
    channel_add = State()
    channel_del = State()
    broadcast = State()
    storage_channel = State()


def norm_code(text: str) -> str:
    return (text or '').strip().lower().replace(' ', '')[:64]


def parse_post_ref(m: Message):
    """Forward, Telegram post link yoki admin botga yuborgan video/photo/documentni saqlash."""
    chat_id = None
    msg_id = None

    # Eski forward metadata
    if getattr(m, 'forward_from_chat', None) and getattr(m, 'forward_from_message_id', None):
        chat_id = str(m.forward_from_chat.id)
        msg_id = int(m.forward_from_message_id)

    # Aiogram/Telegram yangi forward_origin metadata
    origin = getattr(m, 'forward_origin', None)
    if origin and not chat_id:
        try:
            if getattr(origin, 'chat', None) and getattr(origin, 'message_id', None):
                chat_id = str(origin.chat.id)
                msg_id = int(origin.message_id)
        except Exception:
            pass

    # t.me/username/123 yoki t.me/c/123456789/123
    text = (m.text or m.caption or '').strip()
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

    # Admin to'g'ridan-to'g'ri botga video/document/photo yuborsa ham saqlanadi
    if not chat_id and (m.video or m.document or m.photo or m.animation or m.audio or m.voice):
        chat_id = str(m.chat.id)
        msg_id = int(m.message_id)

    return chat_id, msg_id


def parse_channel_line(text: str):
    """Kanal qo'shish: @kanal yoki https://t.me/kanal yoki Nomi | @kanal | https://t.me/kanal"""
    raw = (text or '').strip()
    parts = [p.strip() for p in raw.split('|')]
    name = 'Kanal'
    chat_id = ''
    link = ''

    for p in parts:
        if not p:
            continue
        if p.startswith('http://') or p.startswith('https://'):
            link = p
            m = re.search(r't\.me/([A-Za-z0-9_]+)', p)
            if m and not chat_id:
                chat_id = '@' + m.group(1)
        elif p.startswith('@') or p.startswith('-100'):
            chat_id = p
            if p.startswith('@') and not link:
                link = 'https://t.me/' + p[1:]
        else:
            name = p[:60]
    if not chat_id and raw.startswith('@'):
        chat_id = raw
        link = 'https://t.me/' + raw[1:]
    if not link and chat_id.startswith('@'):
        link = 'https://t.me/' + chat_id[1:]
    return name, chat_id, link


def sub_kb(channels: list[dict], code: str) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        if ch.get('link'):
            rows.append([InlineKeyboardButton(text=f"📢 {ch.get('name','Kanal')}", url=ch['link'])])
    rows.append([InlineKeyboardButton(text='✅ Tekshirish', callback_data=f'mcheck:{code[:40]}')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def missing_subs(message: Message, bot_id: int, user_id: int) -> list[dict]:
    settings = await get_settings(bot_id)
    channels = settings.get('force_channels', []) or []
    missing = []
    for ch in channels:
        chat_id = ch.get('chat_id') or ''
        if not chat_id:
            continue
        try:
            member = await message.bot.get_chat_member(chat_id, user_id)
            if member.status in {'left', 'kicked'}:
                missing.append(ch)
        except Exception:
            # Bot kanalga admin qilinmagan yoki chat_id xato bo'lsa, userni qiynamaymiz, admin uchun logik xabar bor.
            missing.append(ch)
    return missing


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    async def admin_home(m: Message):
        await m.answer(
            '👮 <b>Kino bot admin panel</b>\n\n'
            '<blockquote>Kinoni kod orqali tarqating. Kino fayllar serverga saqlanmaydi — kanal posti yoki botga yuborilgan xabar ID orqali copy qilinadi.</blockquote>',
            reply_markup=movie_admin(),
        )

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            f'👋 <b>Assalomu alaykum, {m.from_user.full_name}!</b>\n\n'
            '<blockquote>Kino olish uchun kino kodini yuboring.</blockquote>\n\n'
            '🎬 Masalan: <code>avatar1</code>',
        )

    @r.message(Command('admin'))
    async def admin(m: Message):
        if m.from_user.id != owner_id:
            return
        await admin_home(m)

    @r.callback_query(F.data == 'm:back')
    async def back(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.clear()
        await c.message.answer('👮 <b>Admin panel</b>', reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:help')
    async def help_cb(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await c.message.answer(
            '📚 <b>Qo‘llanma</b>\n\n'
            '<blockquote>1) Kino qo‘shish bosing\n2) Kod yozing\n3) Kino nomini yozing\n4) Kanal postini forward qiling yoki t.me link yuboring\n\n'
            'Bot kino kanalida admin bo‘lsa, user kod yuborganda kinoni copy qilib beradi. Majburiy obuna uchun kanal @username yoki link qo‘shing.</blockquote>',
            reply_markup=movie_admin(),
        )
        await c.answer()

    @r.callback_query(F.data == 'm:add')
    async def add_start(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.code)
        await c.message.answer('🎬 <b>Kino kodini yuboring:</b>\n\nNamuna: <code>avatar1</code>', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.code)
    async def code(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        code = norm_code(m.text or '')
        if not code:
            await m.answer('❌ Kod bo‘sh bo‘lmasin.', reply_markup=cancel_menu()); return
        await state.update_data(code=code)
        await state.set_state(MovieState.title)
        await m.answer('📝 <b>Kino nomini yuboring:</b>\n\nMasalan: <code>Avatar 2 Uzbek tilida</code>', reply_markup=cancel_menu())

    @r.message(MovieState.title)
    async def title(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        await state.update_data(title=(m.text or '').strip()[:120] or 'Kino')
        await state.set_state(MovieState.post)
        await m.answer(
            '📩 <b>Endi kino postini yuboring.</b>\n\n'
            '<blockquote>4 xil usul ishlaydi:\n1) Kanal postini forward qiling\n2) https://t.me/kanal/123 link yuboring\n3) https://t.me/c/123456/123 link yuboring\n4) Video/documentni to‘g‘ridan-to‘g‘ri shu botga yuboring</blockquote>\n\n'
            '⚠️ Kanal posti ishlashi uchun bot o‘sha kanalda admin bo‘lsin.',
            reply_markup=cancel_menu(),
        )

    @r.message(MovieState.post)
    async def post(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        data = await state.get_data()
        chat_id, msg_id = parse_post_ref(m)
        if not chat_id or not msg_id:
            await m.answer('❌ Post aniqlanmadi. Forward qiling, t.me link yuboring yoki video/document yuboring.', reply_markup=cancel_menu())
            return
        await add_movie(bot_id, data['code'], data['title'], str(chat_id), int(msg_id), '')
        await state.clear()
        await m.answer(
            '✅ <b>Kino saqlandi!</b>\n\n'
            f'🎬 Kod: <code>{data["code"]}</code>\n'
            f'📝 Nomi: <b>{data["title"]}</b>\n'
            f'📌 Manba: <code>{chat_id}/{msg_id}</code>',
            reply_markup=movie_admin(),
        )

    @r.callback_query(F.data == 'm:list')
    async def movie_list(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        rows = await list_movies(bot_id)
        if not rows:
            await c.message.answer('📭 <b>Kino yo‘q.</b>', reply_markup=movie_admin())
            await c.answer(); return
        lines = ['📋 <b>Kinolar ro‘yxati</b>\n']
        total_views = 0
        for x in rows:
            total_views += int(x['views'] or 0)
            lock = '🔒' if int(x['is_premium'] or 0) else '✅'
            lines.append(f'{lock} <code>{x["code"]}</code> — {x["title"]} 👁 {x["views"]}')
        lines.append(f'\n<blockquote>Jami ko‘rishlar: {total_views}</blockquote>')
        await c.message.answer('\n'.join(lines), reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:del')
    async def del_start(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.del_code)
        await c.message.answer('🗑 <b>O‘chiriladigan kino kodini yuboring:</b>', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.del_code)
    async def del_code(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        await delete_movie(bot_id, norm_code(m.text or ''))
        await state.clear()
        await m.answer('✅ Kino o‘chirildi.', reply_markup=movie_admin())

    @r.callback_query(F.data == 'm:premium')
    async def prem_start(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.premium_code)
        await c.message.answer('🔐 <b>Premium yoqish/o‘chirish uchun kino kodini yuboring:</b>', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.premium_code)
    async def prem_code(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        code = norm_code(m.text or '')
        movie = await get_movie(bot_id, code)
        if not movie:
            await m.answer('❌ Bunday kod topilmadi.', reply_markup=movie_admin()); await state.clear(); return
        new_val = 0 if int(movie['is_premium'] or 0) else 1
        await set_movie_premium(bot_id, code, new_val)
        await state.clear()
        await m.answer(('🔒 Premium yoqildi.' if new_val else '🔓 Premium o‘chirildi.') + f' Kod: <code>{code}</code>', reply_markup=movie_admin())

    @r.callback_query(F.data == 'm:storage')
    async def storage_channel_panel(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        settings = await get_settings(bot_id)
        st = settings.get('movie_channel') or {}
        if st.get('chat_id'):
            text = (
                '📺 <b>Kino kanal sozlamasi</b>\n\n'
                f'<blockquote>📢 Kanal: {st.get("name", "Kino kanal")}\n'
                f'🆔 Chat ID: {st.get("chat_id", "")}\n'
                f'🔗 Link: {st.get("link", "-")}\n\n'
                'Bot kanalga admin qilingan bo‘lsa, kanal postidan kinoni copy qilib beradi.</blockquote>'
            )
        else:
            text = (
                '📺 <b>Kino kanal sozlamasi</b>\n\n'
                '<blockquote>Hali kino kanal ulanmagan. Har bir bot egasi o‘z kanalini ulaydi.\n\n'
                'Kanal ulanmasa ham admin video/documentni botga yuborib kino qo‘sha oladi.</blockquote>'
            )
        await c.message.answer(text, reply_markup=movie_channel_menu())
        await c.answer()

    @r.callback_query(F.data == 'm:storage_add')
    async def storage_add(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.storage_channel)
        await c.message.answer(
            '📺 <b>Kino kanal qo‘shish / almashtirish</b>\n\n'
            '<blockquote>Formatlardan bittasini yuboring:\n'
            '1) <code>@kanal_username</code>\n'
            '2) <code>https://t.me/kanal_username</code>\n'
            '3) <code>-1001234567890</code>\n'
            '4) <code>Kino kanal | @kanal_username | https://t.me/kanal_username</code>\n\n'
            '⚠️ Botni o‘sha kanalga admin qiling. Aks holda copyMessage ishlamaydi.</blockquote>',
            reply_markup=cancel_menu(),
        )
        await c.answer()

    @r.message(MovieState.storage_channel)
    async def storage_add_msg(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        name, chat_id, link = parse_channel_line(m.text or '')
        if not chat_id and not link:
            await m.answer('❌ Kanal aniqlanmadi. @username, -100... yoki t.me link yuboring.', reply_markup=cancel_menu()); return
        settings = await get_settings(bot_id)
        settings['movie_channel'] = {'name': name or 'Kino kanal', 'chat_id': chat_id, 'link': link}
        await save_settings(bot_id, settings)
        await state.clear()
        await m.answer(
            '✅ <b>Kino kanal saqlandi!</b>\n\n'
            f'<blockquote>📢 {name}\n🆔 {chat_id}\n🔗 {link or "-"}</blockquote>\n\n'
            'Endi kanal postini forward qiling yoki link orqali kino qo‘shing.',
            reply_markup=movie_admin(),
        )

    @r.callback_query(F.data == 'm:storage_clear')
    async def storage_clear(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        settings = await get_settings(bot_id)
        settings.pop('movie_channel', None)
        await save_settings(bot_id, settings)
        await c.message.answer('🧹 <b>Kino kanal sozlamasi tozalandi.</b>\n\n<blockquote>Endi admin video/documentni botga yuborib yoki yangi kanal ulab kino qo‘shishi mumkin.</blockquote>', reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:cache')
    async def movie_cache_clear(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        settings = await get_settings(bot_id)
        settings['last_cache_clear'] = 'done'
        await save_settings(bot_id, settings)
        await c.message.answer('🧹 <b>Kesh tozalandi.</b>\n\n<blockquote>Bot fayllarni serverda saqlamaydi. Vaqtinchalik holatlar va menyu keshi yangilandi.</blockquote>', reply_markup=movie_admin())
        await c.answer()

    @r.callback_query(F.data == 'm:channels')
    async def channels(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        settings = await get_settings(bot_id)
        chs = settings.get('force_channels', []) or []
        text = '📢 <b>Majburiy obuna kanallari</b>\n\n'
        if not chs:
            text += '<blockquote>Hozircha kanal yo‘q. Qo‘shish tugmasini bosing.</blockquote>'
        else:
            for i, ch in enumerate(chs, 1):
                text += f'{i}. {ch.get("name","Kanal")} — <code>{ch.get("chat_id","")}</code>\n'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='➕ Kanal qo‘shish', callback_data='m:ch_add')],
            [InlineKeyboardButton(text='🗑 Kanal o‘chirish', callback_data='m:ch_del')],
            [InlineKeyboardButton(text='◀️ Orqaga', callback_data='m:back')],
        ])
        await c.message.answer(text, reply_markup=kb)
        await c.answer()

    @r.callback_query(F.data == 'm:ch_add')
    async def ch_add(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.channel_add)
        await c.message.answer(
            '➕ <b>Kanal qo‘shish</b>\n\n'
            '<blockquote>Format:\nKanal nomi | @username | https://t.me/username\n\nYoki faqat @username yuboring.</blockquote>\n\n'
            '⚠️ Botni kanalga admin qiling.',
            reply_markup=cancel_menu(),
        )
        await c.answer()

    @r.message(MovieState.channel_add)
    async def ch_add_msg(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        name, chat_id, link = parse_channel_line(m.text or '')
        if not chat_id and not link:
            await m.answer('❌ Kanal aniqlanmadi. @username yoki t.me link yuboring.', reply_markup=cancel_menu()); return
        settings = await get_settings(bot_id)
        chs = settings.get('force_channels', []) or []
        chs.append({'name': name, 'chat_id': chat_id, 'link': link})
        settings['force_channels'] = chs
        await save_settings(bot_id, settings)
        await state.clear()
        await m.answer(f'✅ Kanal qo‘shildi: <b>{name}</b> <code>{chat_id}</code>', reply_markup=movie_admin())

    @r.callback_query(F.data == 'm:ch_del')
    async def ch_del(c: CallbackQuery, state: FSMContext):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        await state.set_state(MovieState.channel_del)
        await c.message.answer('🗑 O‘chirish uchun kanal tartib raqamini yuboring. Masalan: <code>1</code>', reply_markup=cancel_menu())
        await c.answer()

    @r.message(MovieState.channel_del)
    async def ch_del_msg(m: Message, state: FSMContext):
        if m.from_user.id != owner_id: return
        if (m.text or '').strip() in BACK_WORDS:
            await state.clear(); await admin_home(m); return
        try:
            idx = int((m.text or '').strip()) - 1
            settings = await get_settings(bot_id)
            chs = settings.get('force_channels', []) or []
            removed = chs.pop(idx)
            settings['force_channels'] = chs
            await save_settings(bot_id, settings)
            await m.answer(f'✅ O‘chirildi: {removed.get("name","Kanal")}', reply_markup=movie_admin())
        except Exception:
            await m.answer('❌ Raqam noto‘g‘ri.', reply_markup=movie_admin())
        await state.clear()

    @r.callback_query(F.data == 'm:stats')
    async def stats(c: CallbackQuery):
        if c.from_user.id != owner_id:
            await c.answer('Ruxsat yo‘q', show_alert=True); return
        rows = await list_movies(bot_id)
        total = len(rows)
        views = sum(int(x['views'] or 0) for x in rows)
        prem = sum(1 for x in rows if int(x['is_premium'] or 0))
        await c.message.answer(
            '📊 <b>Statistika</b>\n\n'
            f'<blockquote>🎬 Kinolar: {total} ta\n🔒 Premium: {prem} ta\n👁 Jami ko‘rishlar: {views}</blockquote>',
            reply_markup=movie_admin(),
        )
        await c.answer()

    @r.message(F.text.in_({'📊 Statistika','🎬 Kinolar','🔐 Kanallar','📺 Kino kanal','🎬 Kino qo‘shish','🗑 Kino o‘chirish','⭐ Premium','⚙️ Sozlamalar','👮 Adminlar','📨 Xabar yuborish','🧹 Keshni tozalash','📚 Qo‘llanma'}))
    async def owner_text_menu(m: Message, state: FSMContext):
        if m.from_user.id != owner_id:
            return
        text = (m.text or '').strip()
        if text == '📊 Statistika':
            rows = await list_movies(bot_id)
            total = len(rows)
            views = sum(int(x['views'] or 0) for x in rows)
            prem = sum(1 for x in rows if int(x['is_premium'] or 0))
            await m.answer('📊 <b>Statistika</b>\n\n' + f'<blockquote>🎬 Kinolar: {total} ta\n🔒 Premium: {prem} ta\n👁 Jami ko‘rishlar: {views}</blockquote>', reply_markup=movie_admin_reply())
            return
        if text == '🎬 Kinolar':
            rows = await list_movies(bot_id)
            if not rows:
                await m.answer('📭 <b>Kino yo‘q.</b>', reply_markup=movie_admin_reply())
                return
            lines = ['📋 <b>Kinolar ro‘yxati</b>\n']
            for x in rows:
                lock = '🔒' if int(x['is_premium'] or 0) else '✅'
                lines.append(f'{lock} <code>{x["code"]}</code> — {x["title"]} 👁 {x["views"]}')
            await m.answer('\n'.join(lines), reply_markup=movie_admin_reply())
            return
        if text == '🔐 Kanallar':
            settings = await get_settings(bot_id)
            chs = settings.get('force_channels', []) or []
            msg = '📢 <b>Majburiy obuna kanallari</b>\n\n'
            if not chs:
                msg += '<blockquote>Hozircha kanal yo‘q. Qo‘shish uchun pastdagi tugmani bosing.</blockquote>'
            else:
                for i, ch in enumerate(chs, 1):
                    msg += f'{i}. {ch.get("name","Kanal")} — <code>{ch.get("chat_id","")}</code>\n'
            await m.answer(msg, reply_markup=movie_admin())
            return
        if text in {'📺 Kino kanal','⚙️ Sozlamalar'}:
            settings = await get_settings(bot_id)
            st = settings.get('movie_channel') or {}
            if st.get('chat_id'):
                msg = '📺 <b>Kino kanal sozlamasi</b>\n\n' + f'<blockquote>📢 Kanal: {st.get("name","Kino kanal")}\n🆔 Chat ID: {st.get("chat_id","")}\n🔗 Link: {st.get("link","-")}</blockquote>'
            else:
                msg = '📺 <b>Kino kanal sozlamasi</b>\n\n<blockquote>Hali kino kanal ulanmagan. Kanal qo‘shish uchun pastdagi tugmani bosing.</blockquote>'
            await m.answer(msg, reply_markup=movie_channel_menu())
            return
        if text == '🎬 Kino qo‘shish':
            await state.set_state(MovieState.code)
            await m.answer('🎬 <b>Kino kodini yuboring:</b>\n\nNamuna: <code>avatar1</code>', reply_markup=cancel_menu())
            return
        if text == '🗑 Kino o‘chirish':
            await state.set_state(MovieState.del_code)
            await m.answer('🗑 <b>O‘chiriladigan kino kodini yuboring:</b>', reply_markup=cancel_menu())
            return
        if text == '⭐ Premium':
            await state.set_state(MovieState.premium_code)
            await m.answer('🔐 <b>Premium yoqish/o‘chirish uchun kino kodini yuboring:</b>', reply_markup=cancel_menu())
            return
        if text == '👮 Adminlar':
            await m.answer(f'👮 <b>Admin</b>\n\n<blockquote>Asosiy admin ID: <code>{owner_id}</code>\nBu bot egasi shu ID orqali admin paneldan foydalanadi.</blockquote>', reply_markup=movie_admin_reply())
            return
        if text == '📨 Xabar yuborish':
            await m.answer('📨 <b>Xabar yuborish</b>\n\n<blockquote>Ommaviy xabar moduli tayyor menyuda turibdi. Keyingi kengaytmada user bazasiga yuborish ulanadi.</blockquote>', reply_markup=movie_admin_reply())
            return
        if text == '🧹 Keshni tozalash':
            settings = await get_settings(bot_id)
            settings['last_cache_clear'] = 'done'
            await save_settings(bot_id, settings)
            await m.answer('🧹 <b>Kesh tozalandi.</b>', reply_markup=movie_admin_reply())
            return
        if text == '📚 Qo‘llanma':
            await m.answer('📚 <b>Qo‘llanma</b>\n\n<blockquote>1) Kino kanalni ulang yoki video/documentni botga yuboring\n2) Kino qo‘shish bosing\n3) Kod, nom va postni yuboring\n4) User kod yuborsa, bot kinoni copy qilib beradi.</blockquote>', reply_markup=movie_admin_reply())
            return

    @r.callback_query(F.data.startswith('mcheck:'))
    async def check_sub(c: CallbackQuery):
        code = c.data.split(':', 1)[1]
        fake_msg = c.message
        missing = await missing_subs(fake_msg, bot_id, c.from_user.id)
        if missing:
            await c.answer('❌ Hali hamma kanalga obuna emassiz.', show_alert=True)
            return
        movie = await get_movie(bot_id, code)
        if not movie:
            await c.answer('Kod topilmadi', show_alert=True); return
        try:
            await c.message.bot.copy_message(chat_id=c.message.chat.id, from_chat_id=movie['chat_id'], message_id=movie['message_id'])
            await increment_movie_views(bot_id, code)
            await c.answer('✅ Tekshirildi')
        except Exception as e:
            await c.message.answer('⚠️ Kino yuborilmadi. Admin botni kanalga admin qilishi kerak.\n<code>' + str(e)[:200] + '</code>')
            await c.answer()

    @r.message(F.text)
    async def by_code(m: Message):
        text = (m.text or '').strip()
        if text.startswith('/'):
            return
        if m.from_user.id == owner_id and text in {'📊 Statistika','🎬 Kinolar','🔐 Kanallar','📺 Kino kanal','🎬 Kino qo‘shish','🗑 Kino o‘chirish','⭐ Premium','⚙️ Sozlamalar','👮 Adminlar','📨 Xabar yuborish','🧹 Keshni tozalash','📚 Qo‘llanma'}:
            return
        code = norm_code(text)
        movie = await get_movie(bot_id, code)
        if not movie:
            await m.answer('❌ Bunday kod topilmadi. Kodni tekshirib yuboring.')
            return
        if int(movie['is_premium'] or 0) and m.from_user.id != owner_id:
            await m.answer('🔒 <b>Bu premium kino.</b>\n\n<blockquote>Premium olish uchun bot adminiga murojaat qiling.</blockquote>')
            return
        if m.from_user.id != owner_id:
            missing = await missing_subs(m, bot_id, m.from_user.id)
            if missing:
                await m.answer(
                    '📢 <b>Kinoni olish uchun avval kanallarga obuna bo‘ling.</b>\n\n'
                    '<blockquote>Obuna bo‘lgach “✅ Tekshirish” tugmasini bosing.</blockquote>',
                    reply_markup=sub_kb(missing, code),
                )
                return
        try:
            await m.bot.copy_message(chat_id=m.chat.id, from_chat_id=movie['chat_id'], message_id=movie['message_id'])
            await increment_movie_views(bot_id, code)
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            await m.answer('⚠️ Kino yuborilmadi. Botni kino kanaliga admin qiling yoki linkni tekshiring.\n<code>' + str(e)[:200] + '</code>')
        except Exception as e:
            await m.answer('⚠️ Xatolik: <code>' + str(e)[:200] + '</code>')

    dp.include_router(r)
