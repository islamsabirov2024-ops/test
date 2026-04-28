from __future__ import annotations
import asyncio, os, re, tempfile
from aiogram import Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from app import db

URL_RE=re.compile(r'(https?://\S+)')

def menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='📥 Link yuborish')],[KeyboardButton(text='📘 Qo‘llanma')]],resize_keyboard=True)

def setup(dp:Dispatcher,bid:int,owner:int):
    async def start(m:Message):
        await m.answer('📥 <b>Yuklovchi bot</b>\n\n<blockquote>TikTok, Instagram, YouTube link yuboring. Bot video/audio ma’lumotini topishga urinadi.</blockquote>',reply_markup=menu())

    async def helpmsg(m:Message):
        await m.answer('📘 Qo‘llanma\n\n<blockquote>1) Link yuboring\n2) Bot yt-dlp orqali tekshiradi\n3) Kichik fayl bo‘lsa yuboradi\n4) Bo‘lmasa nomi va qidiruv tugmasini beradi</blockquote>')

    async def handle(m:Message):
        text=m.text or ''
        mm=URL_RE.search(text)
        if not mm: return
        url=mm.group(1)
        await m.answer('⏳ Link tekshirilyapti...')
        try:
            import yt_dlp
            tmp=tempfile.mkdtemp(prefix='dlbot_')
            ydl_opts={'outtmpl':os.path.join(tmp,'%(title).80s.%(ext)s'),'format':'mp4/best[filesize<50000000]/best','quiet':True,'noplaylist':True,'max_filesize':50_000_000}
            def run():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info=ydl.extract_info(url,download=True)
                    filename=ydl.prepare_filename(info)
                    return info, filename
            info, filename=await asyncio.to_thread(run)
            title=info.get('title') or 'Video'
            await db.add_download_log(bid,m.from_user.id,url,title)
            if os.path.exists(filename) and os.path.getsize(filename)<50_000_000:
                await m.answer_document(open(filename,'rb'),caption=f'✅ {title}')
            else:
                await m.answer(f'✅ Topildi: <b>{title}</b>\n\nFayl katta yoki yuklab bo‘lmadi.')
        except Exception as e:
            await m.answer(f'❌ Yuklab bo‘lmadi. Sabab: <code>{str(e)[:300]}</code>')

    dp.message.register(start,F.text=='/start')
    dp.message.register(helpmsg,F.text=='📘 Qo‘llanma')
    dp.message.register(handle)
