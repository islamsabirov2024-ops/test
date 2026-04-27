from __future__ import annotations
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.config import SUPER_ADMIN_ID, PAYMENT_CARD, PAYMENT_CARD_HOLDER, PAYMENT_PAYME_LINK, PAYMENT_VISA_INFO
from app.states import CreateBot
from app.services.validator import validate_bot_token
from app.keyboards.common import main_menu, bot_types, tariff_kb, pay_kb, pay_admin, manage_bot, delete_confirm, back_menu, cancel_menu, TARIFFS, money, BACK, CANCEL
from app.db import add_user, create_user_bot, list_user_bots, get_bot, set_bot_status, delete_bot, set_bot_tariff, create_payment, get_payment, pending_payments, set_payment_status, add_bot_days, expire_due_bots
TYPE_TITLE={'movie':'🎬 Kino bot','ad_cleaner':'🧹 Reklama tozalovchi','music_finder':'🎵 Qo‘shiq topuvchi','invite_gate':'👥 Invite bot','it_lessons':'💻 IT darslik','downloader':'📥 Yuklovchi bot'}
router=Router(); manager=None
def set_manager(m):
    global manager; manager=m
def is_admin(uid:int): return uid==SUPER_ADMIN_ID
def home(): return '🤖 <b>Glavni SaaS Bot</b>\n\n<blockquote>Bu bot orqali odamlar o‘z tokeni bilan kino bot, qorovul bot, qo‘shiq topuvchi va IT darslik bot ochadi. To‘lov skrinshoti adminga boradi, tasdiqlansa bot ishlaydi.</blockquote>'
def pay_text(bot_id:int,tariff='start'):
    t=TARIFFS[tariff]
    return f'💳 <b>To‘lov</b>\n\n<blockquote>Bot ID: {bot_id}\nTarif: {t["title"]}\nMuddat: {t["days"]} kun\nSumma: {money(t["price"])} so‘m\nKarta: <code>{PAYMENT_CARD}</code>\nKarta egasi: {PAYMENT_CARD_HOLDER}\nPayme: {PAYMENT_PAYME_LINK or "kiritilmagan"}\nVisa: {PAYMENT_VISA_INFO}</blockquote>\n\nPulni yuboring va chek rasmini tashlang.'
def bot_card(b):
    t=TARIFFS.get(b['tariff_code'] or 'start',TARIFFS['start']); st={'active':'🟢 Active','pending_payment':'⏳ To‘lov kutilmoqda','stopped':'⏸ O‘chirilgan','expired':'⌛ Muddati tugagan','rejected':'❌ Rad etilgan'}.get(b['status'],b['status'])
    return f'🤖 <b>@{b["bot_username"] or b["bot_name"]}</b>\n\n<blockquote>Turi: {TYPE_TITLE.get(b["bot_type_code"],b["bot_type_code"])}\nTarif: {t["title"]}\nNarx: {money(t["price"])} so‘m\nLimit: {t["users"]}\nStatus: {st}\nTugash: {b["expires_at"] or "to‘lovdan keyin"}</blockquote>'
@router.message(CommandStart())
async def start(m:Message,state:FSMContext):
    await state.clear(); u=m.from_user; await add_user(u.id,u.full_name,u.username or '',1 if is_admin(u.id) else 0); await m.answer(home(),reply_markup=main_menu(is_admin(u.id)))
@router.message(F.text.in_({BACK,CANCEL}))
async def back(m:Message,state:FSMContext): await state.clear(); await m.answer('🏠 Asosiy menyu',reply_markup=main_menu(is_admin(m.from_user.id)))
@router.message(F.text=='💳 Tariflar')
async def tariffs(m:Message):
    txt='💳 <b>Tariflar</b>\n'
    for k,t in TARIFFS.items(): txt+=f'\n{t["title"]}\n<blockquote>{money(t["price"])} so‘m / {t["days"]} kun\nLimit: {t["users"]}</blockquote>'
    await m.answer(txt,reply_markup=main_menu(is_admin(m.from_user.id)))
@router.message(F.text=='➕ Bot yaratish')
async def newbot(m:Message,state:FSMContext): await state.set_state(CreateBot.bot_type); await m.answer('➕ <b>Bot turini tanlang</b>',reply_markup=bot_types())
@router.callback_query(F.data.startswith('type:'))
async def typ(c:CallbackQuery,state:FSMContext):
    t=c.data.split(':')[1]; await state.update_data(bot_type=t); await state.set_state(CreateBot.token); await c.message.answer(f'{TYPE_TITLE.get(t,t)} tanlandi.\n\n🔑 BotFather tokenini yuboring.',reply_markup=cancel_menu()); await c.answer()
@router.message(CreateBot.token)
async def token(m:Message,state:FSMContext):
    tok=(m.text or '').strip(); ok,info=await validate_bot_token(tok)
    if not ok: await m.answer('❌ Token noto‘g‘ri. BotFather’dan qayta oling.'); return
    await state.update_data(token=tok,username=info.get('username','')); await state.set_state(CreateBot.name); await m.answer(f'✅ Token OK: @{info.get("username","")}\n\nBot nomini yozing.',reply_markup=cancel_menu())
@router.message(CreateBot.name)
async def name(m:Message,state:FSMContext):
    d=await state.get_data(); bid=await create_user_bot(m.from_user.id,d['token'],d.get('username',''),(m.text or 'Mening botim')[:80],d['bot_type'])
    await state.update_data(bot_id=bid); await state.set_state(CreateBot.tariff); await m.answer('💳 Endi tarif tanlang:',reply_markup=tariff_kb(bid))
@router.callback_query(F.data.startswith('tariff:'))
async def tariff(c:CallbackQuery,state:FSMContext):
    _,bid,tar=c.data.split(':'); bid=int(bid); await set_bot_tariff(bid,tar); await state.update_data(bot_id=bid,tariff=tar); await state.set_state(CreateBot.receipt)
    await c.message.answer(pay_text(bid,tar),reply_markup=cancel_menu()); await c.answer()
@router.message(CreateBot.receipt)
async def receipt(m:Message,state:FSMContext):
    d=await state.get_data(); bid=int(d['bot_id']); tar=d.get('tariff','start'); t=TARIFFS[tar]
    fid=m.photo[-1].file_id if m.photo else (m.document.file_id if m.document else '')
    if not fid: await m.answer('❌ Chekni rasm yoki document qilib yuboring.'); return
    pid=await create_payment(m.from_user.id,bid,t['price'],t['days'],tar,fid); b=await get_bot(bid)
    await m.answer('⏳ Chek adminga yuborildi. Tasdiqlansa bot avtomatik active bo‘ladi.',reply_markup=main_menu(False))
    cap=f'💳 <b>Yangi to‘lov</b>\n<blockquote>Payment: {pid}\nUser: <code>{m.from_user.id}</code>\nBot: @{b["bot_username"]}\nTuri: {TYPE_TITLE.get(b["bot_type_code"])}\nTarif: {t["title"]}\nSumma: {money(t["price"])} so‘m</blockquote>'
    if SUPER_ADMIN_ID:
        try: await m.bot.send_photo(SUPER_ADMIN_ID,fid,caption=cap,reply_markup=pay_admin(pid))
        except Exception: await m.bot.send_message(SUPER_ADMIN_ID,cap,reply_markup=pay_admin(pid))
    await state.clear()
@router.callback_query(F.data.startswith('payok:'))
async def approve(c:CallbackQuery):
    if not is_admin(c.from_user.id): await c.answer('Faqat admin',show_alert=True); return
    pid=int(c.data.split(':')[1]); p=await get_payment(pid)
    if not p: await c.answer('Topilmadi',show_alert=True); return
    await set_payment_status(pid,'approved'); exp=await add_bot_days(int(p['user_bot_id']),int(p['days'])); await set_bot_status(int(p['user_bot_id']),'active')
    msg='Manager yo‘q'
    if manager:
        ok,msg=await manager.start_child(dict(await get_bot(int(p['user_bot_id']))))
    try: await c.bot.send_message(int(p['user_id']),f'✅ To‘lov tasdiqlandi!\n<blockquote>Bot: @{p["bot_username"]}\nTugash: {exp}</blockquote>')
    except Exception: pass
    await c.message.answer('✅ Tasdiqlandi. '+msg); await c.answer()
@router.callback_query(F.data.startswith('payno:'))
async def reject(c:CallbackQuery):
    if not is_admin(c.from_user.id): await c.answer('Faqat admin',show_alert=True); return
    pid=int(c.data.split(':')[1]); p=await get_payment(pid); await set_payment_status(pid,'rejected')
    if p: await set_bot_status(int(p['user_bot_id']),'rejected')
    await c.message.answer('❌ Rad etildi.'); await c.answer()
@router.message(F.text=='🧾 To‘lovlar')
async def pays(m:Message):
    if not is_admin(m.from_user.id): return
    ps=await pending_payments()
    if not ps: await m.answer('✅ Kutilayotgan to‘lov yo‘q.'); return
    for p in ps: await m.answer(f'💳 Payment #{p["id"]}\n<blockquote>Bot: @{p["bot_username"]}\nSumma: {money(p["amount"])} so‘m</blockquote>',reply_markup=pay_admin(p['id']))
@router.message(F.text=='🤖 Botlarim')
async def bots(m:Message):
    bs=await list_user_bots(m.from_user.id)
    if not bs: await m.answer('📭 Sizda bot yo‘q.',reply_markup=main_menu(is_admin(m.from_user.id))); return
    for b in bs: await m.answer(bot_card(b),reply_markup=manage_bot(b['id'],b['status']=='active'))
@router.callback_query(F.data.startswith('open:'))
async def openb(c:CallbackQuery):
    bid=int(c.data.split(':')[1]); b=await get_bot(bid)
    if not b or b['owner_user_id']!=c.from_user.id: await c.answer('Ruxsat yo‘q',show_alert=True); return
    await c.message.answer(bot_card(b),reply_markup=manage_bot(bid,b['status']=='active')); await c.answer()
@router.callback_query(F.data.startswith('run:'))
async def run(c:CallbackQuery):
    bid=int(c.data.split(':')[1]); b=await get_bot(bid)
    if not b or b['owner_user_id']!=c.from_user.id: await c.answer('Ruxsat yo‘q',show_alert=True); return
    if b['status'] not in {'active','stopped'} or not b['expires_at']:
        await c.message.answer(pay_text(bid,b['tariff_code'] or 'start'),reply_markup=pay_kb(bid)); await c.answer(); return
    ok,msg=await manager.start_child(dict(b)) if manager else (False,'Manager yo‘q')
    if ok: await set_bot_status(bid,'active')
    await c.message.answer(('✅ ' if ok else '⚠️ ')+msg); await c.answer()
@router.callback_query(F.data.startswith('stop:'))
async def stop(c:CallbackQuery):
    bid=int(c.data.split(':')[1]); b=await get_bot(bid)
    if not b or b['owner_user_id']!=c.from_user.id: await c.answer('Ruxsat yo‘q',show_alert=True); return
    await set_bot_status(bid,'stopped')
    if manager: await manager.stop_child(bid)
    await c.message.answer('⏸ Bot o‘chirildi.'); await c.answer()
@router.callback_query(F.data.startswith('delete:'))
async def delask(c:CallbackQuery): await c.message.answer('🗑 O‘chirishni tasdiqlaysizmi?',reply_markup=delete_confirm(int(c.data.split(':')[1]))); await c.answer()
@router.callback_query(F.data.startswith('delok:'))
async def delok(c:CallbackQuery):
    bid=int(c.data.split(':')[1]); await delete_bot(bid,c.from_user.id)
    if manager: await manager.stop_child(bid)
    await c.message.answer('🗑 Bot o‘chirildi.'); await c.answer()
@router.callback_query(F.data.startswith('tariffs:'))
async def tariff_open(c:CallbackQuery): await c.message.answer('💳 Tarif tanlang:',reply_markup=tariff_kb(int(c.data.split(':')[1]))); await c.answer()
@router.message(F.text=='👤 Kabinet')
async def cabinet(m:Message): await m.answer(f'👤 <b>Kabinet</b>\n<blockquote>ID: <code>{m.from_user.id}</code>\nBotlarim bo‘limidan botlaringizni boshqaring.</blockquote>',reply_markup=main_menu(is_admin(m.from_user.id)))
@router.message(F.text=='📞 Support')
async def support(m:Message): await m.answer('📞 Support: adminga murojaat qiling.')
@router.message(F.text=='📊 Admin statistika')
async def adminstat(m:Message):
    if is_admin(m.from_user.id): await m.answer('📊 Admin statistika: to‘lovlar va botlar nazorati ishlayapti.')
async def expire_loop(bot, mgr):
    import asyncio
    while True:
        try:
            due=await expire_due_bots()
            for b in due:
                await set_bot_status(int(b['id']),'expired')
                await mgr.stop_child(int(b['id']))
                try: await bot.send_message(int(b['owner_user_id']),f'⌛ @{b["bot_username"]} bot muddati tugadi. Qayta to‘lov qiling.')
                except Exception: pass
        except Exception: pass
        await asyncio.sleep(60)
