from __future__ import annotations
import asyncio, re, urllib.parse
from aiogram import Dispatcher
from aiogram.types import Message
from app.keyboards.common import search_buttons
URL_RE=re.compile(r'https?://\S+',re.I)
async def extract_title(url:str):
    try:
        p=await asyncio.create_subprocess_exec('yt-dlp','--no-playlist','--skip-download','--print','%(title)s','--print','%(artist)s','--print','%(track)s',url,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
        out,_=await asyncio.wait_for(p.communicate(),35)
        lines=[x.strip() for x in out.decode(errors='ignore').splitlines() if x.strip() and x.strip()!='NA']
        return ' - '.join(dict.fromkeys(lines[:3]))
    except Exception: return ''
def setup(dp:Dispatcher, bot_id:int, owner_id:int):
    @dp.message()
    async def music(m:Message):
        text=m.text or m.caption or ''
        mm=URL_RE.search(text)
        if not mm:
            await m.answer('🎵 TikTok yoki Instagram link yuboring. Audio bo‘lsa caption/file nomidan qidiruv tugmasi beraman.'); return
        url=mm.group(0); await m.answer('🔎 Link tekshirilyapti...')
        title=await extract_title(url)
        if not title: title=text[:80] or 'popular music'
        await m.answer(f'🎵 <b>Topilgan nom:</b>\n<blockquote>{title}</blockquote>\n\nPastdagi tugmalar orqali qidiring:',reply_markup=search_buttons(title))
