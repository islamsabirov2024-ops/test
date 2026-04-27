from __future__ import annotations
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.config import SUPER_ADMIN_ID
from app.db import (
    add_user, create_user_bot, list_user_bots, set_bot_status, get_bot, delete_bot,
    set_bot_tariff, add_bot_days, count_user_bots,
)
from app.keyboards.common import (
    main_menu, bot_types, manage_bot, settings_bot_kb, back_menu, cancel_menu,
    tariff_select_kb, duration_kb, delete_confirm, BACK, CANCEL, TARIFFS, money,
)
from app.states import CreateBot
from app.services.validator import validate_bot_token

TYPE_TITLE = {
    'movie': '🎬 Kino bot',
    'ad_cleaner': '🧹 Reklama tozalovchi bot',
    'music_finder': "🎵 Qo'shiq topuvchi bot",
    'invite_gate': "👥 Odam qo'shib yozish bot",
    'it_lessons': '💻 IT darslik bot',
}
TYPE_DESC = {
    'movie': 'Kino kodlarini saqlaydi. User kod yuborsa, kanal postini copy qilib beradi.',
    'ad_cleaner': 'Guruhdagi ssilka, @kanal, forward va spam matnlarni avtomatik o‘chiradi.',
    'music_finder': 'Audio/voice/video qabul qiladi. Tashqi API ulanganda qo‘shiq nomini topadi.',
    'invite_gate': 'Guruhga qo‘shilgan odamlarni sanaydi, salom beradi va referal yuritadi.',
    'it_lessons': 'IT ni 0 dan professional darajagacha o‘rgatadi: Python, bot, web, database, deploy, SaaS.',
}

router = Router()
manager = None

def set_manager(m):
    global manager
    manager = m

def mask_token(token:str)->str:
    if not token: return '—'
    if len(token) <= 14: return token[:4] + '***'
    return token[:8] + '***' + token[-6:]

def remaining_text(expires_at:str)->str:
    if not expires_at: return 'Muddati belgilanmagan'
    try:
        dt=datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        diff=dt-datetime.now()
        if diff.total_seconds() <= 0: return 'Muddati tugagan'
        days=diff.days
        hours=diff.seconds//3600
        mins=(diff.seconds%3600)//60
        return f'{days} kun {hours} soat {mins} daqiqa'
    except Exception:
        return expires_at

def home_text() -> str:
    return (
        '🤖 <b>MultiBot Builder</b>\n\n'
        '<blockquote>Bu katta bot orqali odamlar o‘ziga kino bot, reklama tozalovchi, qo‘shiq topuvchi va IT darslik botlarini token bilan ochib ishlatadi.</blockquote>\n\n'
        '👇 Kerakli bo‘limni tanlang.'
    )

def tariff_text() -> str:
    parts=['💳 <b>Tariflar</b>\n']
    for code,t in TARIFFS.items():
        parts.append(
            f'\n{t["title"]}\n'
            f'💵 Narxi: {money(t["price"])} so‘m/oy ({money(t["per_day"])} so‘m/kun)\n'
            f'👥 Foydalanuvchilar: {t["users"]}\n'
            f'✅ Javob tezligi: {t["speed"]}\n'
            '────────────'
        )
    return '\n'.join(parts)

def bot_card(b)->str:
    tariff=b['tariff_code'] or 'standard'
    t=TARIFFS.get(tariff, TARIFFS['standard'])
    active='🟢' if b['status']=='active' else '⚪️'
    return (
        f'🤖 <b>Bot: @{b["bot_username"] or b["bot_name"]}</b>\n\n'
        f'<blockquote>🔹 Tarif: {t["title"]}\n'
        f'📊 Kunlik faollik: {t["users"]} — {active} {"Ishlayapti" if b["status"]=="active" else "To‘xtagan"}\n'
        f'💰 Narxi: {money(t["price"])} so‘m/oy ({money(t["per_day"])} so‘m/kun)\n'
        f'⏳ Muddati: {remaining_text(b["expires_at"] or "")}</blockquote>\n\n'
        '📆 Tarifni uzaytirish yoki o‘zgartirish uchun quyidagi tugmalardan foydalaning.'
    )

@router.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    u=m.from_user
    await add_user(u.id, u.full_name, u.username or '', 1 if u.id==SUPER_ADMIN_ID else 0)
    await m.answer(home_text(), reply_markup=main_menu())

@router.message(F.text.in_({BACK, CANCEL}))
async def go_back(m: Message, state: FSMContext):
    await state.clear()
    await m.answer('🏠 <b>Asosiy menyu</b>', reply_markup=main_menu())

@router.callback_query(F.data == 'menu:back')
async def cb_back(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.answer('🏠 <b>Asosiy menyu</b>', reply_markup=main_menu())
    await c.answer()

@router.message(F.text == '➕ Bot yaratish')
async def create_entry(m: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CreateBot.bot_type)
    await m.answer(
        '➕ <b>Bot yaratish</b>\n\n'
        '<blockquote>1) Bot turini tanlang\n2) BotFather token yuboring\n3) Nom bering\n4) Botlarim bo‘limidan ishga tushiring</blockquote>',
        reply_markup=bot_types(),
    )

@router.callback_query(F.data.startswith('type:'))
async def choose_type(c: CallbackQuery, state: FSMContext):
    t=c.data.split(':',1)[1]
    await state.update_data(bot_type=t)
    await state.set_state(CreateBot.token)
    await c.message.answer(
        f'{TYPE_TITLE.get(t,t)} tanlandi.\n\n'
        f'<blockquote>{TYPE_DESC.get(t, "")}</blockquote>\n\n'
        '🔑 BotFather bergan tokenni yuboring.\n'
        'Namuna: <code>123456789:ABCDEF...</code>',
        reply_markup=cancel_menu(),
    )
    await c.answer()

@router.message(CreateBot.token)
async def got_token(m: Message, state: FSMContext):
    token=(m.text or '').strip()
    if token in {BACK, CANCEL}:
        await state.clear(); await m.answer('🏠 <b>Asosiy menyu</b>', reply_markup=main_menu()); return
    ok, info=await validate_bot_token(token)
    if not ok:
        await m.answer('❌ Token noto‘g‘ri yoki ishlamayapti. BotFather’dan qayta oling.', reply_markup=cancel_menu())
        return
    await state.update_data(token=token, bot_username=info.get('username',''))
    await state.set_state(CreateBot.name)
    await m.answer(
        f'✅ Token tekshirildi: @{info.get("username", "")}\n\n'
        '<blockquote>Endi bot uchun ichki nom yozing. Masalan: Mening kino botim</blockquote>',
        reply_markup=cancel_menu(),
    )

@router.message(CreateBot.name)
async def got_name(m: Message, state: FSMContext):
    if (m.text or '').strip() in {BACK, CANCEL}:
        await state.clear(); await m.answer('🏠 <b>Asosiy menyu</b>', reply_markup=main_menu()); return
    data=await state.get_data()
    name=(m.text or '').strip()[:80] or 'Mening botim'
    bot_id=await create_user_bot(m.from_user.id, data['token'], data.get('bot_username',''), name, data['bot_type'])
    await state.clear()
    await m.answer(
        '✅ <b>Bot yaratildi!</b>\n\n'
        f'🤖 Bot: @{data.get("bot_username", "")}\n'
        f'📂 Bot turi: {TYPE_TITLE.get(data["bot_type"])}\n'
        f'💳 Boshlang‘ich tarif: ✅⭐ Standard\n'
        f'📆 Muddati: 30 kun\n\n'
        '<blockquote>Endi “🤖 Botlarim” bo‘limiga kirib, botni sozlang yoki ishga tushiring.</blockquote>',
        reply_markup=main_menu(),
    )

@router.message(F.text == '🤖 Botlarim')
async def my_bots(m: Message):
    bots=await list_user_bots(m.from_user.id)
    if not bots:
        await m.answer('📭 <b>Bot yo‘q.</b>\n\n<blockquote>➕ Bot yaratish bo‘limidan yangi bot oching.</blockquote>', reply_markup=main_menu())
        return
    await m.answer('📋 <b>Quyidagi botlardan birini tanlang:</b>', reply_markup=back_menu())
    for b in bots:
        await m.answer(f'⚙️ <b>@{b["bot_username"] or b["bot_name"]}</b>', reply_markup=manage_bot(b['id'], b['status']=='active'))

@router.callback_query(F.data == 'menu:my_bots')
async def menu_my_bots(c: CallbackQuery):
    bots=await list_user_bots(c.from_user.id)
    if not bots: await c.message.answer('📭 Bot yo‘q.', reply_markup=main_menu())
    else:
        await c.message.answer('📋 <b>Quyidagi botlardan birini tanlang:</b>', reply_markup=back_menu())
        for b in bots: await c.message.answer(f'⚙️ <b>@{b["bot_username"] or b["bot_name"]}</b>', reply_markup=manage_bot(b['id'], b['status']=='active'))
    await c.answer()

@router.callback_query(F.data.startswith('bot:'))
async def open_bot(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    await c.message.answer(bot_card(b), reply_markup=manage_bot(bot_id, b['status']=='active'))
    await c.answer()

@router.callback_query(F.data.startswith('settings:'))
async def settings(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    await c.message.answer(
        '⚙️ <b>Bot sozlamalari</b>\n\n'
        f'🤖 Bot: <b>@{b["bot_username"] or b["bot_name"]}</b>\n'
        f'🔑 Token: <code>{mask_token(b["bot_token"])}</code>\n'
        f'📆 Yaratilgan: {b["created_at"]}\n'
        f'👤 Admin: <code>{b["admin_id"] or b["owner_user_id"]}</code>\n\n'
        f'📂 Bot turi: <b>{TYPE_TITLE.get(b["bot_type_code"], b["bot_type_code"])}</b>',
        reply_markup=settings_bot_kb(bot_id, b['status']=='active'),
    )
    await c.answer()

@router.callback_query(F.data.startswith('run:'))
async def run_bot(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    ok,msg=await manager.start_child(dict(b)) if manager else (False, 'Manager yo‘q')
    if ok: await set_bot_status(bot_id, 'active')
    await c.message.answer(('✅ <b>Bot ishga tushdi.</b>\n' if ok else '⚠️ <b>Xatolik.</b>\n') + f'<blockquote>{msg}</blockquote>')
    await c.answer()

@router.callback_query(F.data.startswith('stop:'))
async def stop_bot(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    await set_bot_status(bot_id, 'stopped')
    if manager: await manager.stop_child(bot_id)
    await c.message.answer('⏸ <b>Bot to‘xtatildi.</b>')
    await c.answer()

@router.callback_query(F.data.startswith('delete:'))
async def ask_delete(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1])
    await c.message.answer('🗑 <b>Botni o‘chirishni tasdiqlaysizmi?</b>', reply_markup=delete_confirm(bot_id))
    await c.answer()

@router.callback_query(F.data.startswith('delok:'))
async def del_bot(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); await delete_bot(bot_id, c.from_user.id)
    if manager: await manager.stop_child(bot_id)
    await c.message.answer('🗑 <b>Bot o‘chirildi.</b>', reply_markup=main_menu())
    await c.answer()

@router.callback_query(F.data.startswith('tariff:'))
async def tariff_change(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    await c.message.answer(tariff_text(), reply_markup=tariff_select_kb(bot_id))
    await c.answer()

@router.callback_query(F.data.startswith('settariff:'))
async def set_tariff(c: CallbackQuery):
    _, bot_id, tariff = c.data.split(':')
    bot_id=int(bot_id); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    await set_bot_tariff(bot_id, tariff)
    t=TARIFFS.get(tariff, TARIFFS['standard'])
    await c.message.answer(
        f'🤖 <b>@{b["bot_username"]}</b> uchun qancha muddatga to‘lov qilmoqchisiz?\n\n'
        f'<blockquote>🔹 Tarif: {t["title"]}\n💵 Narxi: {money(t["price"])} so‘m ({money(t["per_day"])} so‘m/kun)\n⏳ Muddatni tanlang</blockquote>\n\n'
        '📆 <b>Necha kunlik to‘lov qilmoqchisiz?</b>',
        reply_markup=duration_kb(bot_id, tariff),
    )
    await c.answer()

@router.callback_query(F.data.startswith('paydays:'))
async def pay_days(c: CallbackQuery):
    bot_id=int(c.data.split(':')[1]); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    tariff=b['tariff_code'] or 'standard'; t=TARIFFS.get(tariff, TARIFFS['standard'])
    await c.message.answer(
        f'🤖 <b>@{b["bot_username"]}</b> uchun qancha muddatga to‘lov qilmoqchisiz?\n\n'
        f'<blockquote>🔹 Tarif: {t["title"]}\n💵 Narxi: {money(t["price"])} so‘m ({money(t["per_day"])} so‘m/kun)\n⏳ Muddati: {remaining_text(b["expires_at"] or "")}</blockquote>\n\n'
        '📆 <b>Necha kunlik to‘lov qilmoqchisiz?</b>',
        reply_markup=duration_kb(bot_id, tariff),
    )
    await c.answer()

@router.callback_query(F.data.startswith('pay:'))
async def pay_extend(c: CallbackQuery):
    _, bot_id, tariff, days = c.data.split(':')
    bot_id=int(bot_id); days=int(days); b=await get_bot(bot_id)
    if not b or b['owner_user_id'] != c.from_user.id: await c.answer('Ruxsat yo‘q', show_alert=True); return
    t=TARIFFS.get(tariff, TARIFFS['standard'])
    amount=t['per_day']*days
    new_date=await add_bot_days(bot_id, days)
    await c.message.answer(
        '✅ <b>To‘lov muddati uzaytirildi.</b>\n\n'
        f'<blockquote>🤖 Bot: @{b["bot_username"]}\n🔹 Tarif: {t["title"]}\n📆 Kun: {days}\n💵 Summa: {money(amount)} so‘m\n⏳ Yangi muddat: {new_date}</blockquote>'
    )
    await c.answer()

@router.callback_query(F.data.startswith(('dashboard:', 'newtoken:', 'transfer:', 'adminid:', 'clearcache:')))
async def not_ready_buttons(c: CallbackQuery):
    await c.message.answer('⚙️ <b>Bo‘lim tayyor.</b>\n\n<blockquote>Bu tugma menyuda bor. Kerak bo‘lsa keyingi versiyada ichki amali ham alohida ulanadi.</blockquote>')
    await c.answer()

@router.message(F.text == '💳 Tariflar')
async def tariffs_msg(m: Message):
    await m.answer(tariff_text(), reply_markup=back_menu())

@router.message(F.text == '🧾 Shaxsiy kabinet')
@router.message(F.text == '👤 Profil')
async def profile(m: Message):
    cnt=await count_user_bots(m.from_user.id)
    await m.answer(
        '🧾 <b>Shaxsiy kabinet</b>\n\n'
        f'<blockquote>🆔 ID: {m.from_user.id}\n👤 Ism: {m.from_user.full_name}\n🤖 Botlar soni: {cnt}\n💰 Balans: 0 so‘m</blockquote>',
        reply_markup=back_menu(),
    )

@router.message(F.text.in_({'🫂 Referal', '🚀 Saytga kirish', "💳 Hisob to'ldirish", '📨 Murojaat', "📚 Qo'llanma", '📞 Support'}))
async def simple_pages(m: Message):
    text=m.text
    await m.answer(f'{text}\n\n<blockquote>Bu bo‘lim professional menyu sifatida tayyor. To‘lov karta, referal va sayt linki keyin config orqali ulanadi.</blockquote>', reply_markup=back_menu())
