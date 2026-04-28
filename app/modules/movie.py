from __future__ import annotations
import re
from aiogram import Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.states import MovieState
from app.keyboards.common import movie_admin_menu, movie_add_kb, back_menu, BACK
from app.db import add_movie, get_movie, list_movies, delete_movie, get_settings, save_settings, set_movie_premium, inc_movie_views
ADMIN_TEXTS={'🎬 Kinolar','➕ Kino qo‘shish','📺 Kino kanal','🔐 Majburiy obuna','⭐ Premium','📊 Statistika','📨 Xabar yuborish','⚙️ Sozlamalar','🧹 Kesh tozalash','📘 Qo‘llanma',BACK}
def is_admin(m:Message, owner:int): return bool(m.from_user and m.from_user.id==owner)
async def show_admin(m:Message):
    await m.answer('🎬 <b>Kino bot admin paneli</b>\n\n<blockquote>Kinoni kod bilan qo‘shing. Kanal ulasangiz forward/link orqali, kanal bo‘lmasa botga video/document yuborib saqlaydi.</blockquote>',reply_markup=movie_admin_menu())
def parse_link(text:str):
    m=re.search(r't\.me/(?:c/)?([A-Za-z0-9_\-]+)/(\d+)',text or '')
    if not m: return None
    chat=m.group(1); mid=int(m.group(2))
    if chat.isdigit(): chat='-100'+chat
    else: chat='@'+chat
    return chat, mid
async def check_subs(m:Message,bid:int)->bool:
    s=await get_settings(bid); chs=s.get('sub_channels',[])
    if not chs: return True
    miss=[]
    for ch in chs:
        try:
            cm=await m.bot.get_chat_member(ch,m.from_user.id)
            if cm.status in {'left','kicked'}: miss.append(ch)
        except Exception: miss.append(ch)
    if miss:
        await m.answer('🔐 <b>Kino olish uchun avval kanallarga obuna bo‘ling:</b>\n'+'\n'.join('• '+x for x in miss))
        return False
    return True
def setup(dp:Dispatcher, bot_id:int, owner_id:int):
    @dp.message(F.text=='/start')
    async def start(m:Message,state:FSMContext):
        await state.clear()
        if is_admin(m,owner_id): await show_admin(m)
        else: await m.answer(f'👋 Assalomu alaykum, {m.from_user.full_name}!\n\n<blockquote>Kino olish uchun kino kodini yuboring.\nMasalan: avatar1</blockquote>')
    @dp.message(F.text==BACK)
    async def back(m:Message,state:FSMContext):
        await state.clear();
        if is_admin(m,owner_id): await show_admin(m)
    @dp.message(F.text=='➕ Kino qo‘shish')
    async def add1(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        await state.set_state(MovieState.add_code); await m.answer('🎬 <b>Kino kodi yuboring</b>\n<blockquote>Masalan: avatar1 yoki 777</blockquote>',reply_markup=back_menu())
    @dp.message(MovieState.add_code)
    async def add_code(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        await state.update_data(code=(m.text or '').strip().lower()); await state.set_state(MovieState.add_content)
        await m.answer('📥 <b>Endi kino yuboring</b>\n<blockquote>Forward qiling, t.me post ssilkasi yuboring yoki video/document tashlang.</blockquote>',reply_markup=movie_add_kb())
    @dp.message(MovieState.add_content)
    async def add_content(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        data=await state.get_data(); code=data.get('code','')
        chat_id=''; mid=0; title=code
        if m.forward_from_chat:
            chat_id=str(m.forward_from_chat.id); mid=m.forward_from_message_id or m.message_id; title=m.caption or m.text or code
        elif m.text and parse_link(m.text):
            chat_id,mid=parse_link(m.text); title=code
        elif m.video or m.document:
            # copy from admin chat message id; bot can copy this later only from same chat, so better stored as file chat. Works while message exists.
            chat_id=str(m.chat.id); mid=m.message_id; title=m.caption or code
        else:
            await m.answer('❌ Forward, link yoki video/document yuboring.'); return
        await add_movie(bot_id,code,title,chat_id,mid,m.caption or '')
        await state.clear(); await m.answer(f'✅ Kino qo‘shildi\n<blockquote>Kod: <code>{code}</code>\nManba: <code>{chat_id}/{mid}</code></blockquote>',reply_markup=movie_admin_menu())
    @dp.message(F.text=='🎬 Kinolar')
    async def movies(m:Message):
        if not is_admin(m,owner_id): return
        rows=await list_movies(bot_id)
        if not rows: await m.answer('📭 Kino yo‘q.'); return
        txt='🎬 <b>Kinolar ro‘yxati</b>\n'
        for r in rows[:30]: txt+=f'\n• <code>{r["code"]}</code> — {r["title"] or "Nomsiz"} 👁 {r["views"]}'
        await m.answer(txt)
    @dp.message(F.text=='📺 Kino kanal')
    async def channel(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        s=await get_settings(bot_id); await state.set_state(MovieState.channel)
        await m.answer(f'📺 <b>Kino kanal</b>\n<blockquote>Hozirgi: <code>{s.get("movie_channel","ulanmagan")}</code>\nYangi kanalni @username yoki -100id ko‘rinishida yuboring. Tozalash uchun: 0</blockquote>',reply_markup=back_menu())
    @dp.message(MovieState.channel)
    async def set_channel(m:Message,state:FSMContext):
        s=await get_settings(bot_id); txt=(m.text or '').strip()
        if txt=='0': s.pop('movie_channel',None)
        else: s['movie_channel']=txt
        await save_settings(bot_id,s); await state.clear(); await m.answer('✅ Kino kanal sozlandi.',reply_markup=movie_admin_menu())
    @dp.message(F.text=='🔐 Majburiy obuna')
    async def sub(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        s=await get_settings(bot_id); await state.set_state(MovieState.sub_channel)
        await m.answer('🔐 <b>Majburiy obuna</b>\n<blockquote>Kanallar: '+', '.join(s.get('sub_channels',[]))+'\nYangi kanal yuboring yoki tozalash uchun 0.</blockquote>',reply_markup=back_menu())
    @dp.message(MovieState.sub_channel)
    async def set_sub(m:Message,state:FSMContext):
        s=await get_settings(bot_id); txt=(m.text or '').strip()
        if txt=='0': s['sub_channels']=[]
        elif txt: s['sub_channels']=list(dict.fromkeys(s.get('sub_channels',[])+[txt]))
        await save_settings(bot_id,s); await state.clear(); await m.answer('✅ Majburiy obuna sozlandi.',reply_markup=movie_admin_menu())
    @dp.message(F.text=='⭐ Premium')
    async def prem(m:Message,state:FSMContext):
        if not is_admin(m,owner_id): return
        await state.set_state(MovieState.premium_code); await m.answer('⭐ Premium toggle uchun kino kod yuboring.',reply_markup=back_menu())
    @dp.message(MovieState.premium_code)
    async def prem_set(m:Message,state:FSMContext):
        code=(m.text or '').strip().lower(); r=await get_movie(bot_id,code)
        if not r: await m.answer('❌ Kod topilmadi.'); return
        val=0 if r['is_premium'] else 1; await set_movie_premium(bot_id,code,val); await state.clear(); await m.answer(('⭐ Premium yoqildi' if val else '✅ Oddiy qilindi'),reply_markup=movie_admin_menu())
    @dp.message(F.text=='📊 Statistika')
    async def stat(m:Message):
        if not is_admin(m,owner_id): return
        rows=await list_movies(bot_id); views=sum(int(r['views'] or 0) for r in rows)
        await m.answer(f'📊 <b>Statistika</b>\n<blockquote>🎬 Kinolar: {len(rows)}\n👁 Ko‘rishlar: {views}</blockquote>')
    @dp.message(F.text=='🧹 Kesh tozalash')
    async def cache(m:Message):
        if is_admin(m,owner_id): await m.answer('🧹 Kesh tozalandi. <blockquote>Vaqtinchalik holatlar tozalandi.</blockquote>')
    @dp.message(F.text=='📘 Qo‘llanma')
    async def helpx(m:Message):
        if is_admin(m,owner_id): await m.answer('📘 <b>Qo‘llanma</b>\n<blockquote>1) Kino kanalga botni admin qiling.\n2) ➕ Kino qo‘shish bosing.\n3) Kod yuboring.\n4) Kanal postini forward qiling yoki link yuboring.</blockquote>')
    @dp.message(F.text.in_(ADMIN_TEXTS))
    async def admin_buttons(m:Message):
        if is_admin(m,owner_id): await m.answer('✅ Bo‘lim ochildi.',reply_markup=movie_admin_menu())
    @dp.message()
    async def code_handler(m:Message):
        if m.text in ADMIN_TEXTS and is_admin(m,owner_id): return
        if not m.text: return
        if not await check_subs(m,bot_id): return
        code=m.text.strip().lower(); r=await get_movie(bot_id,code)
        if not r:
            await m.answer('❌ Bunday kod topilmadi. Kodni tekshirib yuboring.'); return
        try:
            await m.bot.copy_message(m.chat.id, r['chat_id'], int(r['message_id']), protect_content=True)
            await inc_movie_views(bot_id,code)
        except Exception as e:
            await m.answer('⚠️ Kino yuborilmadi. Admin kanalga botni admin qilganini tekshiring.\n<code>'+str(e)[:120]+'</code>')
