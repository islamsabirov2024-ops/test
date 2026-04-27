from __future__ import annotations
import re
from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states import CleanerState
from app.keyboards.common import cleaner_menu, cleaner_settings_kb, back_menu, BACK
from app.db import get_settings, save_settings, add_clean_log, last_clean_logs
LINK_RE=re.compile(r'(https?://\S+|www\.\S+|t\.me/\S+|telegram\.me/\S+)',re.I)
MENTION_RE=re.compile(r'(?<!\w)@[A-Za-z0-9_]{4,}',re.I)
SPAM_WORDS={'reklama','podpiska','obuna bo','pul ishlash','stavka','kazino','bet','bonus'}
def defaults(s):
    d={'links':1,'mentions':1,'forward':1,'buttons':1,'words':1,'ban':0,'blacklist':[],'whitelist':[]}
    d.update(s or {}); return d
def setup(dp:Dispatcher, bot_id:int, owner_id:int):
    @dp.message(F.text=='/start')
    async def start(m:Message):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            await m.answer('🧹 <b>Qorovul bot paneli</b>\n<blockquote>Guruhga admin qiling va BotFather’da privacy disable qiling. Ssilka, @kanal, forward va spamni o‘chiradi.</blockquote>',reply_markup=cleaner_menu())
    @dp.message(F.text=='🟢 Status')
    async def status(m:Message):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            s=defaults(await get_settings(bot_id)); await m.answer('🟢 <b>Status</b>\n<blockquote>Bot ishlayapti.\nSsilka: '+str(s['links'])+'\n@kanal: '+str(s['mentions'])+'\nForward: '+str(s['forward'])+'</blockquote>')
    @dp.message(F.text=='⚙️ Sozlamalar')
    async def settings(m:Message):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            await m.answer('⚙️ <b>Filtrlarni yoqish/o‘chirish</b>',reply_markup=cleaner_settings_kb(defaults(await get_settings(bot_id))))
    @dp.callback_query(F.data.startswith('cl:t:'))
    async def toggle(c:CallbackQuery):
        if c.from_user.id!=owner_id: await c.answer('Ruxsat yo‘q',show_alert=True); return
        key=c.data.split(':')[-1]; s=defaults(await get_settings(bot_id)); s[key]=0 if s.get(key,1) else 1; await save_settings(bot_id,s)
        await c.message.edit_reply_markup(reply_markup=cleaner_settings_kb(s)); await c.answer('Saqlandi')
    @dp.message(F.text=='🚫 Blacklist')
    async def black(m:Message,state:FSMContext):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            s=defaults(await get_settings(bot_id)); await state.set_state(CleanerState.add_black); await m.answer('🚫 <b>Blacklist</b>\n<blockquote>'+', '.join(s['blacklist'])+'\nYangi so‘z yuboring. Tozalash: 0</blockquote>',reply_markup=back_menu())
    @dp.message(CleanerState.add_black)
    async def set_black(m:Message,state:FSMContext):
        s=defaults(await get_settings(bot_id)); txt=(m.text or '').strip().lower()
        if txt=='0': s['blacklist']=[]
        elif txt and txt!=BACK: s['blacklist']=list(dict.fromkeys(s['blacklist']+[txt]))
        await save_settings(bot_id,s); await state.clear(); await m.answer('✅ Blacklist saqlandi.',reply_markup=cleaner_menu())
    @dp.message(F.text=='✅ Whitelist')
    async def white(m:Message,state:FSMContext):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            s=defaults(await get_settings(bot_id)); await state.set_state(CleanerState.add_white); await m.answer('✅ <b>Whitelist</b>\n<blockquote>'+', '.join(s['whitelist'])+'\nRuxsat berilgan domen/@kanal yuboring. Tozalash: 0</blockquote>',reply_markup=back_menu())
    @dp.message(CleanerState.add_white)
    async def set_white(m:Message,state:FSMContext):
        s=defaults(await get_settings(bot_id)); txt=(m.text or '').strip().lower()
        if txt=='0': s['whitelist']=[]
        elif txt and txt!=BACK: s['whitelist']=list(dict.fromkeys(s['whitelist']+[txt]))
        await save_settings(bot_id,s); await state.clear(); await m.answer('✅ Whitelist saqlandi.',reply_markup=cleaner_menu())
    @dp.message(F.text=='📜 Log')
    async def logs(m:Message):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            rows=await last_clean_logs(bot_id); txt='📜 <b>Oxirgi o‘chirilganlar</b>\n'
            for r in rows: txt+=f'\n• {r["reason"]} | user:{r["user_id"]}'
            await m.answer(txt or 'Log yo‘q')
    @dp.message(F.text=='🧪 Test')
    async def test(m:Message,state:FSMContext):
        if m.chat.type=='private' and m.from_user.id==owner_id:
            await state.set_state(CleanerState.test); await m.answer('🧪 Test matn yuboring.',reply_markup=back_menu())
    @dp.message(CleanerState.test)
    async def test_check(m:Message,state:FSMContext):
        reason=await detect(m,bot_id,only_reason=True); await state.clear(); await m.answer('Natija: '+(reason or 'toza'),reply_markup=cleaner_menu())
    async def detect(m:Message, bid:int, only_reason=False):
        s=defaults(await get_settings(bid)); text=(m.text or m.caption or '').lower()
        for w in s['whitelist']:
            if w and w in text: return None
        reason=None
        if s['forward'] and (getattr(m,'forward_from_chat',None) or getattr(m,'forward_origin',None)): reason='forward'
        elif s['buttons'] and m.reply_markup: reason='url tugma'
        elif s['links'] and LINK_RE.search(text): reason='ssilka'
        elif s['mentions'] and MENTION_RE.search(text): reason='@kanal'
        elif s['words'] and any(w in text for w in SPAM_WORDS.union(set(s['blacklist']))): reason='spam so‘z'
        return reason
    @dp.message()
    async def cleaner(m:Message):
        if m.chat.type not in {'group','supergroup'}: return
        reason=await detect(m,bot_id)
        if not reason: return
        try: await m.delete()
        except Exception: return
        await add_clean_log(bot_id,m.chat.id,m.from_user.id if m.from_user else 0,reason,m.text or m.caption or '')
