from __future__ import annotations
import asyncio
import re
from urllib.parse import quote_plus
from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

URL_RE = re.compile(r'(https?://\S+)', re.I)
SUPPORTED = ('tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com', 'instagram.com', 'www.instagram.com')


def search_kb(query: str) -> InlineKeyboardMarkup:
    q = quote_plus(query or '')
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔎 YouTube’dan qidirish', url=f'https://www.youtube.com/results?search_query={q}')],
        [InlineKeyboardButton(text='🔎 Google’dan qidirish', url=f'https://www.google.com/search?q={q}')],
        [InlineKeyboardButton(text='🎵 TikTok’da qidirish', url=f'https://www.tiktok.com/search?q={q}')],
    ])


def clean_title(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r'#\S+', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s[:160]


def build_query(info: dict) -> tuple[str, str]:
    # yt-dlp TikTok uchun ko‘pincha track/artist yoki music_* maydonlarini beradi.
    title = clean_title(info.get('track') or info.get('alt_title') or info.get('title') or '')
    artist = clean_title(info.get('artist') or info.get('creator') or info.get('uploader') or '')
    album = clean_title(info.get('album') or '')
    if artist and title and artist.lower() not in title.lower():
        query = f'{artist} - {title}'
    else:
        query = title or artist or album
    pretty = query or 'Qo‘shiq nomi aniqlanmadi'
    return pretty, query


async def extract_metadata(url: str) -> tuple[bool, str, dict]:
    def run():
        try:
            import yt_dlp
        except Exception:
            return False, 'yt-dlp o‘rnatilmagan. requirements.txt orqali o‘rnating.', {}
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'noplaylist': True,
            'socket_timeout': 25,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return True, 'ok', info or {}
        except Exception as e:
            return False, str(e)[:260], {}
    return await asyncio.to_thread(run)


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(
            '🎵 <b>Qo‘shiq topuvchi bot</b>\n\n'
            '<blockquote>Instagram Reels yoki TikTok ssilka yuboring. Bot videodagi music/title ma’lumotini olib, qo‘shiq nomini chiqaradi va YouTube/Google qidiruv tugmalarini beradi.</blockquote>\n\n'
            '✅ Bepul ishlaydi: <code>yt-dlp</code> orqali metadata o‘qiladi.\n'
            '⚠️ Instagram ba’zan login/cookie talab qilishi mumkin.'
        )

    @r.message(Command('help'))
    async def help_cmd(m: Message):
        await m.answer(
            '📚 <b>Qo‘llanma</b>\n\n'
            '<blockquote>1) TikTok yoki Instagram Reels link yuboring\n2) Bot music/title ma’lumotini tekshiradi\n3) Topilgan nom bo‘yicha qidiruv tugmalari beradi</blockquote>\n\n'
            'Namuna: <code>https://www.tiktok.com/@user/video/...</code>'
        )

    @r.message(F.text.regexp(r'https?://'))
    async def link_music(m: Message):
        text = m.text or ''
        match = URL_RE.search(text)
        if not match:
            await m.answer('🔗 TikTok yoki Instagram ssilka yuboring.')
            return
        url = match.group(1).strip()
        if not any(d in url.lower() for d in SUPPORTED):
            await m.answer('⚠️ Hozircha faqat TikTok va Instagram Reels linklari qo‘llab-quvvatlanadi.')
            return
        wait = await m.answer('⏳ <b>Tekshiryapman...</b>\n<blockquote>Video ma’lumotidan qo‘shiq nomini ajratyapman.</blockquote>')
        ok, err, info = await extract_metadata(url)
        if not ok:
            await wait.answer(
                '⚠️ <b>Qo‘shiqni avtomatik topib bo‘lmadi.</b>\n\n'
                f'<blockquote>{err}</blockquote>\n\n'
                'Instagram/TikTok ba’zan yopiq yoki login talab qiladi. Link ochiq bo‘lsa qayta yuboring.'
            )
            return
        pretty, query = build_query(info)
        uploader = clean_title(info.get('uploader') or info.get('creator') or '')
        video_title = clean_title(info.get('title') or '')
        duration = info.get('duration')
        dur = f'{int(duration)//60}:{int(duration)%60:02d}' if isinstance(duration, (int, float)) else '—'
        out = (
            '✅ <b>Natija topildi</b>\n\n'
            f'<blockquote>🎵 Qo‘shiq/nom: <b>{pretty}</b>\n'
            f'👤 Muallif: {uploader or "—"}\n'
            f'🎬 Video title: {video_title or "—"}\n'
            f'⏱ Davomiyligi: {dur}</blockquote>\n\n'
            '👇 To‘liq qo‘shiqni topish uchun qidiruv tugmalaridan foydalaning.'
        )
        await wait.answer(out, reply_markup=search_kb(query or pretty))

    @r.message(F.audio | F.voice | F.video | F.document)
    async def file_music(m: Message):
        name = ''
        obj = m.audio or m.voice or m.video or m.document
        if getattr(obj, 'file_name', None):
            name = obj.file_name.rsplit('.', 1)[0]
        if getattr(obj, 'title', None):
            name = f'{getattr(obj, "performer", "") or ""} {obj.title}'.strip()
        if name:
            await m.answer(
                '🎧 <b>Fayldan nom olindi</b>\n\n'
                f'<blockquote>{name}</blockquote>\n\n'
                '👇 Qidiruv tugmalaridan foydalaning.',
                reply_markup=search_kb(name),
            )
        else:
            await m.answer(
                '🎧 Fayl qabul qilindi.\n\n'
                '<blockquote>Bepul variant fayl ichidagi qo‘shiqni Shazam kabi eshitib topmaydi. TikTok/Instagram link yuborsangiz metadata orqali topishga urinadi.</blockquote>'
            )

    @r.message()
    async def other(m: Message):
        await m.answer('🎵 TikTok yoki Instagram Reels ssilka yuboring.')

    dp.include_router(r)
