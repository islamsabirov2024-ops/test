import asyncio, logging, time, re, datetime, copy
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart, StateFilter, StateFilter, StateFilter, StateFilter
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramConflictError
from . import db
from .config import BOT_TOKEN, SUPER_ADMIN_ID, BOT_NAME, SUBSCRIPTION_FAKE_VERIFY
from .keyboards import *
from .states import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
log=logging.getLogger(__name__)
child_tasks={}; runtime_cache={}; spam_cache={}
NO_PREVIEW=LinkPreviewOptions(is_disabled=True)
main_router=Router(); child_router=Router()
nav_stack={}
main_pending_topups={}
broadcast_queue=[]

def remember_nav(user_id:int, menu:str):
    nav_stack[user_id]=menu

def parent_menu(menu:str):
    if menu in {'content'}: return 'admin'
    if menu in {'settings'}: return 'admin'
    if menu in {'ads','admins','protect','texts','pay','premium','referral','antispam','channels','cache'}: return 'settings'
    if menu in {'movie_edit','movie_list'}: return 'content'
    return 'admin'

def is_admin(uid:int): return uid==SUPER_ADMIN_ID
async def runtime_db_id(runtime_bot_id:int):
    if runtime_bot_id in runtime_cache: return runtime_cache[runtime_bot_id]['id']
    for r in await db.bots():
        try:
            b=Bot(r['token']); me=await b.get_me(); await b.session.close()
            if me.id==runtime_bot_id:
                runtime_cache[runtime_bot_id]={'id':r['id'],'owner':r['owner_id']}; return r['id']
        except Exception: pass
    return 0
async def child_owner_by_runtime(runtime_bot_id:int):
    if runtime_bot_id not in runtime_cache: await runtime_db_id(runtime_bot_id)
    return runtime_cache.get(runtime_bot_id,{}).get('owner',0)
async def is_child_admin(m:Message):
    bid=await runtime_db_id(m.bot.id); owner=await child_owner_by_runtime(m.bot.id)
    return m.from_user.id==owner or is_admin(m.from_user.id) or await db.is_bot_admin(bid,m.from_user.id)
async def log_action(bot_id, admin_id, action, details=''):
    try: await db.add_log(bot_id,admin_id,action,details)
    except Exception: pass

def fmt_money(x): return f"{int(x):,}".replace(',', ' ')
def fmt_dt(ts): return datetime.datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')
def parse_schedule(text):
    t=(text or '').strip().lower()
    if t in {'0','hozir','now','bugun'}: return 0
    m=re.match(r'^(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})$', t)
    if m:
        return int(datetime.datetime(*map(int,m.groups())).timestamp())
    m=re.match(r'^(\d+)\s*(minut|daq|minute|m)$', t)
    if m: return int(time.time())+int(m.group(1))*60
    m=re.match(r'^(\d+)\s*(soat|hour|h)$', t)
    if m: return int(time.time())+int(m.group(1))*3600
    return 0



def normalize_channel_input(raw: str):
    raw=(raw or '').strip()
    if not raw:
        return '', ''
    if raw.startswith('-100') or raw.lstrip('-').isdigit():
        return raw, ''
    if raw.startswith('@'):
        return raw, 'https://t.me/' + raw.lstrip('@')
    if raw.startswith('https://t.me/'):
        tail=raw.replace('https://t.me/','').strip('/')
        if tail.startswith('+') or tail.startswith('joinchat/'):
            return raw, raw
        return '@' + tail.split('/')[0], raw
    if raw.startswith('t.me/'):
        tail=raw.replace('t.me/','').strip('/')
        if tail.startswith('+') or tail.startswith('joinchat/'):
            return 'https://' + raw, 'https://' + raw
        return '@' + tail.split('/')[0], 'https://' + raw
    return raw, raw if raw.startswith(('http://','https://')) else ''


async def visible_force_channels(bot_id:int, only_missing=None):
    rows = only_missing if only_missing is not None else await db.channels(bot_id)
    result = []
    seen = set()
    for ch in rows:
        title = ch['title'] or ''
        url = ch['url'] or ''
        chat = str(ch['chat_id'] or '')
        if not url:
            if chat.startswith('@'):
                url = 'https://t.me/' + chat.lstrip('@')
            elif chat.startswith('t.me/'):
                url = 'https://' + chat
            elif chat.startswith('https://t.me/'):
                url = chat
        if url and not url.startswith(('http://','https://')):
            if url.startswith('@'):
                url = 'https://t.me/' + url.lstrip('@')
            elif url.startswith('t.me/'):
                url = 'https://' + url
        key = (chat, url)
        if key in seen:
            continue
        seen.add(key)
        if not url:
            continue
        result.append(ch)
    return result

async def check_force_sub(bot: Bot, bot_id: int, user_id: int):
    """Return (ok, missing_channels). Only Telegram channels/groups are validated."""
    chans = await db.channels(bot_id)
    fake = await db.get_setting(bot_id,'sub_fake_verify','0')
    if SUBSCRIPTION_FAKE_VERIFY or fake == '1':
        return True, []
    missing = []
    for ch in chans:
        if not ch['checkable']:
            continue
        chat = str(ch['chat_id'] or '').strip()
        if chat.startswith('http'):
            # Invite links cannot be validated directly. Use forwarded post or -100 id for real validation.
            missing.append(ch)
            continue
        try:
            member = await bot.get_chat_member(chat, user_id)
            if member.status in {'left','kicked'}:
                missing.append(ch)
            else:
                await db.channel_pass(ch['id'])
        except Exception:
            missing.append(ch)
    return len(missing) == 0, missing


def _pay_setting_text(auto_enabled: str, manual_enabled: str) -> str:
    return (
        f"🤖 Avtomat to‘lov: {'✅ Yoniq' if auto_enabled == '1' else '❌ O‘chiq'}\n"
        f"👨‍💼 Admin tasdiq: {'✅ Yoniq' if manual_enabled == '1' else '❌ O‘chiq'}"
    )


def main_topup_admin_buttons(req_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"main_topup_ok:{req_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"main_topup_no:{req_id}")
        ]
    ])

async def add_user_balance_safe(user_id: int, amount: int):
    await db.add_user(user_id, None)
    for name in ("add_balance", "add_user_balance", "increase_balance", "topup_balance"):
        fn = getattr(db, name, None)
        if fn:
            try:
                return await fn(user_id, amount)
            except Exception:
                pass
    async with db.conn() as con:
        try:
            await con.execute("UPDATE users SET balance = COALESCE(balance,0) + ? WHERE user_id = ?", (amount, user_id))
            if hasattr(con, "commit"):
                await con.commit()
        except TypeError:
            await con.execute("UPDATE users SET balance = COALESCE(balance,0) + $1 WHERE user_id = $2", amount, user_id)

def _find_auto_link(methods, provider: str) -> str:
    provider = provider.lower()
    for r in methods:
        name = str(r['name']).lower()
        value = str(r['value']).strip()
        if provider in name and (value.startswith('http://') or value.startswith('https://')):
            return value
    return ''

@main_router.message(CommandStart())
async def start(m:Message):
    ref=None
    try:
        if m.text and len(m.text.split())>1: ref=int(m.text.split()[1])
    except Exception: pass
    await db.add_user(m.from_user.id, ref)
    await m.answer(f"👋 Assalomu alaykum, {m.from_user.full_name}!\n\nMenyudan tanlang:", reply_markup=main_menu())
@main_router.message(Command('admin'))
async def admin(m:Message):
    if not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    await m.answer('👑 Super admin panel:', reply_markup=super_menu())
@main_router.message(F.text=='◀️ Orqaga')
async def back(m:Message): await m.answer('Menyudan tanlang...', reply_markup=main_menu())
@main_router.message(F.text=='➕ Bot yaratish')
async def create_bot(m:Message, state:FSMContext):
    await state.clear()
    await m.answer('🤖 Quyidagi bot turlaridan birini tanlang:', reply_markup=bot_types_menu())

@main_router.message(F.text=='🎬 Kino Bot')
async def choose_kino_bot(m:Message, state:FSMContext):
    await db.ensure_platform_tables()
    rows=await db.platform_tariffs(True)
    await state.update_data(kind='kino')
    text = "🎬 Kino Bot — Tariflar\n\n"
    for r in rows:
        limit = 'Cheksiz' if int(r['daily_limit'] or 0)==0 else f"{fmt_money(r['daily_limit'])} ta / Kuniga"
        per_day = int(int(r['monthly_price'])/30) if int(r['monthly_price']) else 0
        text += (
            f"┌ {r['name']}\n"
            f"├ 💵 Narxi: {fmt_money(r['monthly_price'])} so'm/oy ({fmt_money(per_day)} so'm/kun)\n"
            f"├ 👥 Foydalanuvchilar: {limit}\n"
            f"├ ✅ {limit} foydalanuvchi\n"
            f"├ ✅ Javob tezligi: {r['speed']}\n"
            "└──────────────\n\n"
        )
    text += "Davom etish uchun kerakli tarifni tanlang."
    await m.answer(text, reply_markup=platform_tariffs_inline(rows, 0, 'platform_select'))

@main_router.callback_query(F.data.startswith('platform_select:'))
async def platform_select(c:CallbackQuery, state:FSMContext):
    tid=int(c.data.split(':')[1]); t=await db.platform_tariff_by_id(tid)
    if not t: return await c.answer('Tarif topilmadi', show_alert=True)
    u=await db.get_user(c.from_user.id); bal=int(u['balance']) if u else 0
    price=int(t['monthly_price'])
    limit='Cheksiz' if int(t['daily_limit'] or 0)==0 else f"{fmt_money(t['daily_limit'])} odam/kun"
    if bal < price:
        return await c.message.answer(f"❌ Balans yetarli emas.\n\n📦 Tarif: {t['name']}\n💰 Narx: {fmt_money(price)} so'm\n💳 Sizda: {fmt_money(bal)} so'm\n\nAvval 💳 Hisob to'ldirish bo‘limidan balans to‘ldiring.")
    await state.set_state(CreateBot.token)
    await state.update_data(kind='kino', price=price, platform_tariff_id=tid)
    await c.message.answer(
        f"✅ Tarif tanlandi: {t['name']}\n"
        f"💰 Narx: {fmt_money(price)} so'm / 30 kun\n"
        f"👥 Limit: {limit}\n\n"
        "🤖 BotFather’dan olingan bot tokenni yuboring:"
    )
    await c.answer('Tarif tanlandi')

@main_router.message(F.text.startswith('✅ Bot yaratish'))
async def create_kino_confirm(m:Message, state:FSMContext):
    rows=await db.platform_tariffs(True)
    await m.answer('📦 Avval tarif tanlang:', reply_markup=platform_tariffs_inline(rows, 0, 'platform_select'))

@main_router.message(F.text=='💳 Hisob to\'ldirish')
async def topup(m:Message, state:FSMContext):
    await state.clear()
    card=await db.get_global('main_payment_card','')
    payme_enabled=await db.get_global('payme_enabled','0')
    payme_link=await db.get_global('payme_link','')
    txt=(
        "💳 Hisob to‘ldirish\n\n"
        "Bu yer asosiy bot balansi uchun. Bot yaratish/tarif uchun balans to‘ldirasiz.\n\n"
        "✅ 2 xil usul bor:\n"
        "1️⃣ Karta orqali — chek yuborasiz, admin tasdiqlaydi\n"
        "2️⃣ Payme auto — Payme yoqilgan bo‘lsa link orqali to‘laysiz\n\n"
    )
    if card:
        txt += f"💳 Karta:\n{card}\n\n"
    else:
        txt += "❌ Karta raqami kiritilmagan.\n\n"
    if payme_enabled=='1' and payme_link:
        txt += f"⚪ Payme: ✅ Yoniq\n{payme_link}"
    else:
        txt += "⚪ Payme: ❌ O‘chiq"
    await m.answer(txt, reply_markup=topup_menu(), link_preview_options=NO_PREVIEW)

@main_router.message(F.text.in_({'💳 Karta orqali to‘lash','⚪ Payme (Avto)','🔵 Click (Avto)','💳 Karta (Avto)','💳 Humo'}))
async def topup_choose_method(m:Message, state:FSMContext):
    txt=(m.text or '').strip()
    if txt=='⚪ Payme (Avto)':
        enabled=await db.get_global('payme_enabled','0')
        link=await db.get_global('payme_link','')
        if enabled!='1' or not link:
            return await m.answer('❌ Payme hozircha yoqilmagan.\n\nKarta orqali to‘lov qiling yoki admin Payme sozlasin.', reply_markup=topup_menu(), link_preview_options=NO_PREVIEW)
        await state.set_state("main_topup_amount")
        await state.update_data(topup_method='⚪ Payme', topup_card=link)
        return await m.answer(
            '⚪ Payme orqali to‘lov\n\n'
            f'{link}\n\n'
            'To‘lov qilgandan keyin summani yozing va chek yuboring.\n\n'
            '💰 To‘lov miqdorini kiriting:\nMinimal: 1 000 so‘m\nMasalan: 18000',
            reply_markup=rkb([['◀️ Orqaga']]),
            link_preview_options=NO_PREVIEW
        )

    card=await db.get_global('main_payment_card','')
    if not card:
        if is_admin(m.from_user.id):
            return await m.answer('❌ Avval asosiy karta raqamini sozlang.\n\nYo‘li: /admin → ⚙️ Global sozlamalar → 💳 Karta qo‘shish', reply_markup=main_menu())
        return await m.answer('❌ Hozircha karta raqami kiritilmagan. Admin bilan bog‘laning.', reply_markup=main_menu())

    await state.set_state("main_topup_amount")
    await state.update_data(topup_method='💳 Karta', topup_card=card)
    await m.answer(
        "💳 Karta orqali balans to‘ldirish\n\n"
        f"💳 Karta:\n{card}\n\n"
        "Pulni shu kartaga tashlang va summani yozing.\n\n"
        "💰 To‘lov miqdorini kiriting:\nMinimal: 1 000 so‘m\nMasalan: 18000",
        reply_markup=rkb([['◀️ Orqaga']]),
        link_preview_options=NO_PREVIEW
    )


@main_router.message(StateFilter("main_topup_amount"))
async def topup_amount(m:Message, state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await m.answer("Menyudan tanlang...", reply_markup=main_menu())
    raw=(m.text or '').replace(' ','').strip()
    if not raw.isdigit():
        return await m.answer("❌ Faqat summa yozing. Masalan: 18000")
    amount=int(raw)
    if amount < 1000:
        return await m.answer("❌ Minimal summa: 1 000 so‘m")
    data=await state.get_data()
    method=data.get('topup_method','Karta')
    card=data.get('topup_card') or await db.get_global('main_payment_card','')
    await state.set_state("main_topup_receipt")
    await state.update_data(topup_amount=amount)
    await m.answer(
        f"💳 {method} orqali hisob to‘ldirish\n\n"
        f"💰 To‘lov summasi: {fmt_money(amount)} so‘m\n\n"
        "📸 Endi to‘lov chekini rasm yoki document qilib yuboring.\n"
        "Admin tasdiqlagandan keyin balansingizga qo‘shiladi.",
        reply_markup=rkb([['◀️ Orqaga']])
    )

@main_router.message(StateFilter("main_topup_receipt"))
async def topup_receipt(m:Message, state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await m.answer("Menyudan tanlang...", reply_markup=main_menu())
    if not m.photo and not m.document:
        return await m.answer("❌ Chek rasmini yoki documentini yuboring.")
    data=await state.get_data()
    amount=int(data.get('topup_amount',0))
    method=data.get('topup_method','Karta')
    req_id=f"{m.from_user.id}_{int(time.time())}"
    file_id=m.photo[-1].file_id if m.photo else m.document.file_id
    file_type = "photo" if m.photo else "document"
    await db.add_main_topup(req_id, m.from_user.id, amount, method, file_id, file_type)
    cap=("🧾 Yangi balans to‘ldirish cheki\n\n"
         f"👤 User: {m.from_user.id}\n"
         f"💳 Usul: {method}\n"
         f"💰 Summa: {fmt_money(amount)} so‘m\n\n"
         "Tasdiqlasangiz summa foydalanuvchi balansiga qo‘shiladi.")
    try:
        if m.photo:
            await m.bot.send_photo(SUPER_ADMIN_ID, file_id, caption=cap, reply_markup=main_topup_admin_buttons(req_id))
        else:
            await m.bot.send_document(SUPER_ADMIN_ID, file_id, caption=cap, reply_markup=main_topup_admin_buttons(req_id))
    except Exception:
        await m.bot.send_message(SUPER_ADMIN_ID, cap, reply_markup=main_topup_admin_buttons(req_id))
    await state.clear()
    await m.answer("⏳ Chek adminga yuborildi. Tasdiqlangandan keyin balans qo‘shiladi.", reply_markup=main_menu())

@main_router.callback_query(F.data.startswith('main_topup_ok:'))
async def main_topup_ok(c:CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer('Ruxsat yo‘q', show_alert=True)
    req_id=c.data.split(':',1)[1]
    req=await db.get_main_topup(req_id)
    if not req or req['status']!='pending':
        return await c.answer('Bu chek allaqachon ko‘rilgan yoki topilmadi.', show_alert=True)
    await db.set_main_topup_status(req_id, 'approved')
    await add_user_balance_safe(int(req['user_id']), int(req['amount']))
    approved_text = (
        "✅ Balans to‘ldirish TASDIQLANDI!\n\n"
        f"👤 User: {req['user_id']}\n"
        f"💰 Summa: {fmt_money(req['amount'])} so‘m\n"
        f"💳 Usul: {req['method']}\n\n"
        "Tugma bosildi va balansga pul qo‘shildi."
    )
    try:
        await c.message.edit_caption(approved_text, reply_markup=None)
    except Exception:
        try:
            await c.message.edit_text(approved_text, reply_markup=None)
        except Exception:
            await c.message.answer(approved_text)
    try:
        await c.bot.send_message(int(req['user_id']), f"✅ To‘lovingiz tasdiqlandi!\n\n💰 Balansga qo‘shildi: {fmt_money(req['amount'])} so‘m")
    except Exception:
        pass
    await c.answer('✅ Tasdiqlandi')

@main_router.callback_query(F.data.startswith('main_topup_no:'))
async def main_topup_no(c:CallbackQuery):
    if not is_admin(c.from_user.id):
        return await c.answer('Ruxsat yo‘q', show_alert=True)
    req_id=c.data.split(':',1)[1]
    req=await db.get_main_topup(req_id)
    if not req or req['status']!='pending':
        return await c.answer('Bu chek allaqachon ko‘rilgan yoki topilmadi.', show_alert=True)
    await db.set_main_topup_status(req_id, 'rejected')
    rejected_text = (
        "❌ Balans to‘ldirish RAD ETILDI!\n\n"
        f"👤 User: {req['user_id']}\n"
        f"💰 Summa: {fmt_money(req['amount'])} so‘m\n"
        f"💳 Usul: {req['method']}\n\n"
        "Tugma bosildi va chek rad etildi."
    )
    try:
        await c.message.edit_caption(rejected_text, reply_markup=None)
    except Exception:
        try:
            await c.message.edit_text(rejected_text, reply_markup=None)
        except Exception:
            await c.message.answer(rejected_text)
    try:
        await c.bot.send_message(int(req['user_id']), "❌ To‘lov chekingiz rad etildi. Iltimos, to‘g‘ri chek yuboring.")
    except Exception:
        pass
    await c.answer('❌ Rad etildi')

@main_router.message(F.text.in_({'💳 To‘lovlar', "💳 To'lovlar"}))
async def main_payments_admin(m:Message):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    pending=[(k,v) for k,v in main_pending_topups.items() if v.get('status')=='pending']
    if not pending:
        return await m.answer('💳 To‘lovlar\n\nHozircha kutilayotgan chek yo‘q.', reply_markup=super_menu())
    txt='💳 Kutilayotgan to‘lovlar:\n\n'
    for k,v in pending:
        txt+=f"• {k} | User: {v['user_id']} | {fmt_money(v['amount'])} so‘m | {v['method']}\n"
    await m.answer(txt, reply_markup=super_menu())

@main_router.message(F.text=='📚 Qo\'llanma')
async def guide(m:Message):
    await m.answer('📚 Qo‘llanma\n\n1️⃣ ➕ Bot yaratish ni bosing\n2️⃣ 🎬 Kino Bot ni tanlang\n3️⃣ BotFather tokenini yuboring\n4️⃣ Yaratilgan botga kirib /panel bosing\n5️⃣ Kanal, premium, to‘lov va kinolarni sozlang')

@main_router.message(F.text=='📩 Murojaat')
async def support(m:Message): await m.answer('📩 Murojaat uchun admin ID: '+str(SUPER_ADMIN_ID))

@main_router.message(F.text=='🚀 Saytga kirish')
async def site(m:Message): await m.answer('🚀 Sayt havolasi admin tomonidan keyin ulanadi.')

@main_router.message(F.text=='⚙️ Global sozlamalar')
async def global_settings(m:Message):
    if not is_admin(m.from_user.id): return
    await m.answer('⚙️ Global sozlamalar:', reply_markup=global_settings_menu())

@main_router.message(F.text=='📋 Hozirgi sozlamalar')
async def current_settings(m:Message):
    if not is_admin(m.from_user.id): return
    price=await db.get_global('create_price','0'); bonus=await db.get_global('referral_bonus','0')
    await m.answer(f'📋 Hozirgi sozlamalar\n\n💰 Bot yaratish narxi: {fmt_money(price)} so‘m\n🎁 Referal bonus: {fmt_money(bonus)} so‘m', reply_markup=global_settings_menu())


@main_router.message(F.text=='📦 Platforma tariflari')
async def platform_tariffs_admin(m:Message):
    if not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    rows=await db.platform_tariffs(False)
    txt='📦 Platforma tariflari:\n\n'
    for r in rows:
        limit='Cheksiz' if int(r['daily_limit'] or 0)==0 else f"{fmt_money(r['daily_limit'])} odam/kun"
        st='✅' if int(r['active']) else '❌'
        txt+=f"{r['id']}. {st} {r['name']} — {fmt_money(r['monthly_price'])} so‘m/oy — {limit} — {r['speed']}\n"
    await m.answer(txt, reply_markup=platform_admin_menu())

@main_router.message(F.text=='➕ Platforma tarif qo‘shish')
async def platform_add1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    await state.set_state(MainTariffAdmin.name); await m.answer('📦 Tarif nomini kiriting. Masalan: ⭐ Standard')
@main_router.message(MainTariffAdmin.name)
async def platform_add2(m:Message,state:FSMContext):
    await state.update_data(name=m.text); await state.set_state(MainTariffAdmin.monthly_price); await m.answer('💵 Oylik narxni kiriting. Masalan: 18000')
@main_router.message(MainTariffAdmin.monthly_price)
async def platform_add3(m:Message,state:FSMContext):
    await state.update_data(monthly_price=int(m.text.strip())); await state.set_state(MainTariffAdmin.daily_limit); await m.answer('👥 Kunlik user limitini kiriting. Cheksiz uchun 0.')
@main_router.message(MainTariffAdmin.daily_limit)
async def platform_add4(m:Message,state:FSMContext):
    await state.update_data(daily_limit=int(m.text.strip())); await state.set_state(MainTariffAdmin.speed); await m.answer('⚡ Javob tezligini yozing. Masalan: ~0.4s')
@main_router.message(MainTariffAdmin.speed)
async def platform_add5(m:Message,state:FSMContext):
    d=await state.get_data(); await db.add_platform_tariff(d['name'], d['monthly_price'], d['daily_limit'], m.text.strip()); await state.clear(); await m.answer('✅ Platforma tarifi qo‘shildi', reply_markup=platform_admin_menu())

@main_router.message(F.text=='✏️ Platforma tarif o‘zgartirish')
async def platform_edit1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    await state.set_state(MainTariffAdmin.edit_id); await m.answer('✏️ O‘zgartiriladigan tarif ID raqamini yuboring:')
@main_router.message(MainTariffAdmin.edit_id)
async def platform_edit2(m:Message,state:FSMContext):
    await state.update_data(edit_id=int(m.text.strip())); await state.set_state(MainTariffAdmin.edit_field); await m.answer('Nimani o‘zgartiramiz?\nname / monthly_price / daily_limit / speed / active')
@main_router.message(MainTariffAdmin.edit_field)
async def platform_edit3(m:Message,state:FSMContext):
    field=m.text.strip()
    if field not in {'name','monthly_price','daily_limit','speed','active'}: return await m.answer('❌ Noto‘g‘ri field.')
    await state.update_data(edit_field=field); await state.set_state(MainTariffAdmin.edit_value); await m.answer('Yangi qiymatni yuboring:')
@main_router.message(MainTariffAdmin.edit_value)
async def platform_edit4(m:Message,state:FSMContext):
    d=await state.get_data(); await db.update_platform_tariff(d['edit_id'], d['edit_field'], m.text.strip()); await state.clear(); await m.answer('✅ Platforma tarifi yangilandi', reply_markup=platform_admin_menu())

@main_router.message(F.text=='🗑 Platforma tarif o‘chirish')
async def platform_del1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    await state.set_state(MainTariffAdmin.delete_id); await m.answer('🗑 O‘chiriladigan tarif ID raqamini yuboring:')
@main_router.message(MainTariffAdmin.delete_id)
async def platform_del2(m:Message,state:FSMContext):
    await db.delete_platform_tariff(int(m.text.strip())); await state.clear(); await m.answer('✅ Tarif o‘chirildi', reply_markup=platform_admin_menu())

@main_router.message(F.text=='💰 Bot yaratish narxi')
async def set_create_price1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.set_state(GlobalSetting.create_price); await m.answer('💰 Yangi bot yaratish narxini kiriting. Masalan: 9000')

@main_router.message(GlobalSetting.create_price)
async def set_create_price2(m:Message,state:FSMContext):
    await db.set_global('create_price', max(0,int(m.text.strip()))); await state.clear(); await m.answer('✅ Bot yaratish narxi saqlandi', reply_markup=global_settings_menu())

@main_router.message(F.text=='🎁 Referal bonus summasi')
async def set_ref_bonus1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    await state.set_state(GlobalSetting.referral_bonus); await m.answer('🎁 Har bir referal uchun bonus summasini kiriting. Masalan: 200')

@main_router.message(GlobalSetting.referral_bonus)
async def set_ref_bonus2(m:Message,state:FSMContext):
    await db.set_global('referral_bonus', max(0,int(m.text.strip()))); await state.clear(); await m.answer('✅ Referal bonus summasi saqlandi', reply_markup=global_settings_menu())


@main_router.message(F.text=='💳 Asosiy karta raqami')
async def set_main_card1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    current=await db.get_global('main_payment_card','')
    await state.set_state('set_main_payment_card')
    await m.answer(
        '💳 Asosiy bot uchun karta raqamini yuboring.\n\n'
        f'Hozirgi karta:\n{current or "kiritilmagan"}\n\n'
        'Masalan:\n8600 0000 0000 0000\nSABIROV ISLOMBEK',
        reply_markup=rkb([['◀️ Orqaga']])
    )

@main_router.message(StateFilter('set_main_payment_card'))
async def set_main_card2(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await m.answer('Bekor qilindi.', reply_markup=global_settings_menu())
    card=(m.text or '').strip()
    if len(card)<8:
        return await m.answer('❌ Karta ma’lumoti juda qisqa. Karta raqami va egasini yuboring.')
    await db.set_global('main_payment_card', card)
    await state.clear()
    await m.answer('✅ Asosiy karta raqami saqlandi!\n\n'+card, reply_markup=global_settings_menu())



@main_router.message(F.text.in_({'💳 Asosiy karta raqami','💳 Karta qo‘shish'}))
async def set_main_card1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    current=await db.get_global('main_payment_card','')
    await state.set_state('set_main_payment_card')
    await m.answer(
        '💳 Asosiy bot uchun karta raqamini yuboring.\n\n'
        f'Hozirgi karta:\n{current or "kiritilmagan"}\n\n'
        'Masalan:\n8600 0000 0000 0000\nSABIROV ISLOMBEK',
        reply_markup=rkb([['◀️ Orqaga']])
    )

@main_router.message(StateFilter('set_main_payment_card'))
async def set_main_card2(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await m.answer('Bekor qilindi.', reply_markup=global_settings_menu())
    card=(m.text or '').strip()
    if len(card)<8:
        return await m.answer('❌ Karta ma’lumoti juda qisqa. Karta raqami va egasini yuboring.')
    await db.set_global('main_payment_card', card)
    await state.clear()
    await m.answer('✅ Asosiy karta raqami saqlandi!\n\n'+card, reply_markup=global_settings_menu())

@main_router.message(F.text=='🗑 Karta o‘chirish')
async def delete_main_card(m:Message):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    await db.set_global('main_payment_card','')
    await m.answer('🗑 Asosiy karta raqami o‘chirildi.', reply_markup=global_settings_menu())

@main_router.message(F.text=='🔘 Payme ON/OFF')
async def payme_toggle(m:Message):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    cur=await db.get_global('payme_enabled','0')
    new='0' if cur=='1' else '1'
    await db.set_global('payme_enabled', new)
    await m.answer(f"⚪ Payme holati: {'✅ Yoniq' if new=='1' else '❌ O‘chiq'}", reply_markup=global_settings_menu())

@main_router.message(F.text=='⚪ Payme sozlash')
async def payme_setup1(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id):
        return await m.answer('⛔ Ruxsat yo‘q')
    current=await db.get_global('payme_link','')
    await state.set_state('set_payme_link')
    await m.answer(
        '⚪ Payme to‘lov linkini yoki instruktsiyasini yuboring.\n\n'
        f'Hozirgi:\n{current or "kiritilmagan"}\n\n'
        'Masalan: https://payme.uz/... yoki Payme merchant link',
        reply_markup=rkb([['◀️ Orqaga']])
    )

@main_router.message(StateFilter('set_payme_link'))
async def payme_setup2(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await m.answer('Bekor qilindi.', reply_markup=global_settings_menu())
    val=(m.text or '').strip()
    if len(val)<5:
        return await m.answer('❌ Payme link/instruktsiya juda qisqa.')
    await db.set_global('payme_link', val)
    await db.set_global('payme_enabled','1')
    await state.clear()
    await m.answer('✅ Payme sozlandi va yoqildi!\n\n'+val, reply_markup=global_settings_menu())


@main_router.message(F.text=='📱 Shaxsiy kabinet')
async def cabinet(m:Message):
    u=await db.get_user(m.from_user.id); refs=await db.ref_count(m.from_user.id)
    await m.answer(f"🪪 ID: {m.from_user.id}\n├ 💼 Balansingiz: {fmt_money(u['balance'] if u else 0)} so‘m\n├ 👥 Referallaringiz: {refs} ta\n├ 🤖 Botlaringiz: {len(await db.bots(m.from_user.id))} ta\n└ 💰 Kiritgan pullaringiz: 0 so‘m")
@main_router.message(F.text=='📊 Umumiy statistika')
async def stats(m:Message):
    if not is_admin(m.from_user.id): return
    s=await db.stat()
    await m.answer(
        f"📊 Umumiy statistika PRO\n\n"
        f"👥 Foydalanuvchilar: {s['users']} ta\n"
        f"🤖 Botlar: {s['bots']} ta\n"
        f"🎬 Kinolar: {s['movies']} ta\n"
        f"💳 To‘lovlar: {s['payments']} ta\n\n"
        f"⚙️ Global sozlamalar orqali bot narxi va referal bonusni boshqaring.",
        reply_markup=super_menu()
    )
@main_router.message(F.text=='🤖 Barcha botlar')
async def allbots(m:Message):
    if not is_admin(m.from_user.id): return
    rows=await db.bots(); await m.answer('🤖 Barcha botlar:\n'+'\n'.join([f"{r['id']}. @{r['username']} | owner {r['owner_id']} | {r['status']}" for r in rows]) if rows else 'Bot yo‘q')

@main_router.message(Command('cancel'))
async def main_cancel(m:Message, state:FSMContext):
    await state.clear()
    await m.answer('✅ Jarayon bekor qilindi.', reply_markup=main_menu())

@child_router.message(Command('cancel'))
async def child_cancel(m:Message, state:FSMContext):
    await state.clear()
    owner=await child_owner_by_runtime(m.bot.id)
    adminflag= m.from_user.id==owner or is_admin(m.from_user.id) or await db.is_bot_admin(await runtime_db_id(m.bot.id),m.from_user.id)
    await m.answer('✅ Jarayon bekor qilindi.', reply_markup=kino_user_menu(adminflag))


@main_router.message(CreateBot.token)
async def create_bot_token(m:Message, state:FSMContext):
    token=(m.text or '').strip()
    if token in {'◀️ Orqaga','/cancel'}:
        await state.clear()
        return await m.answer('✅ Jarayon bekor qilindi.', reply_markup=main_menu())

    data=await state.get_data()
    price=int(data.get('price') or 0)
    tariff_id=int(data.get('platform_tariff_id') or 0)

    # Token formatni tez tekshirish
    if ':' not in token or len(token) < 30:
        return await m.answer(
            '❌ Token noto‘g‘ri ko‘rinadi.\n\n'
            'BotFatherdan olingan tokenni to‘liq yuboring.\n'
            'Masalan: 123456789:AA....'
        )

    # Balansni yana bir marta tekshiramiz va pulni yechamiz
    u=await db.get_user(m.from_user.id)
    bal=int(u['balance']) if u else 0
    if bal < price:
        await state.clear()
        return await m.answer(
            f"❌ Balans yetarli emas.\n\n"
            f"💰 Tarif narxi: {fmt_money(price)} so‘m\n"
            f"💳 Sizda: {fmt_money(bal)} so‘m\n\n"
            "Avval 💳 Hisob to‘ldirish bo‘limidan balans to‘ldiring.",
            reply_markup=main_menu()
        )

    # Token real ishlaydimi tekshiramiz
    test_bot=None
    try:
        test_bot=Bot(token)
        me=await test_bot.get_me()
    except Exception as e:
        return await m.answer(
            '❌ Token ishlamadi.\n\n'
            'Tekshiring:\n'
            '1. Tokenni BotFatherdan to‘liq copy qiling\n'
            '2. Bot tokenini boshqa joyda ishlatayotgan bo‘lmang\n'
            f'Xato: {str(e)[:120]}'
        )
    finally:
        if test_bot:
            try:
                await test_bot.session.close()
            except Exception:
                pass

    # Dublikat token bo‘lsa xato bermasdan tushunarli javob
    old_bot=None
    try:
        for r in await db.bots():
            if str(r['token']) == token:
                old_bot=r
                break
    except Exception:
        old_bot=None
    if old_bot:
        await state.clear()
        return await m.answer(
            f"❌ Bu token oldin qo‘shilgan.\n\n"
            f"Bot: @{old_bot['username']}\n"
            "Botlarim bo‘limidan boshqaring yoki boshqa token yuboring.",
            reply_markup=main_menu()
        )

    # Pul yechish
    paid=await db.take_balance(m.from_user.id, price)
    if not paid:
        await state.clear()
        return await m.answer('❌ Balans yechishda xatolik. Qayta urinib ko‘ring.', reply_markup=main_menu())

    # Botni DBga saqlash
    try:
        bot_id=await db.add_bot(m.from_user.id, token, me.username, me.full_name or me.username)
        await db.activate_platform_for_bot(bot_id, tariff_id, 30)
    except Exception as e:
        # saqlashda xato bo‘lsa pulni qaytarish
        try:
            await db.add_balance(m.from_user.id, price)
        except Exception:
            pass
        await state.clear()
        return await m.answer(
            '❌ Botni saqlashda xatolik bo‘ldi. Balans qaytarildi.\n\n'
            f'Xato: {str(e)[:120]}',
            reply_markup=main_menu()
        )

    # Ishga tushirish
    started=False
    try:
        started=await start_child(bot_id)
    except Exception:
        started=False

    await state.clear()
    await m.answer(
        f"✅ Kino Bot yaratildi!\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"🆔 ID: {bot_id}\n"
        f"💰 Yechildi: {fmt_money(price)} so‘m\n"
        f"⏳ Muddat: 30 kun\n\n"
        f"{'🟢 Bot ishga tushdi.' if started else '🟡 Bot saqlandi. Manager 30 soniya ichida ishga tushiradi.'}\n\n"
        "Endi yangi botga kiring va /panel bosing.",
        reply_markup=main_menu()
    )


@main_router.message(StateFilter(None), F.text)
async def main_stub(m:Message): await m.answer('✅ Bu bo‘lim admin paneldan sozlanadi.', reply_markup=main_menu())

# CHILD BASIC
@child_router.message(CommandStart())
async def child_start(m:Message):
    bid=await runtime_db_id(m.bot.id)
    ref=None
    try:
        if m.text and len(m.text.split())>1: ref=int(m.text.split()[1])
    except Exception: ref=None
    await db.add_user(m.from_user.id, ref)
    if ref and ref != m.from_user.id:
        bonus=int(await db.get_setting(bid,'referral_bonus','0') or 0)
        if bonus>0: await db.add_referral_balance(bid, ref, bonus)
    owner=await child_owner_by_runtime(m.bot.id)
    adminflag= m.from_user.id==owner or is_admin(m.from_user.id) or await db.is_bot_admin(bid,m.from_user.id)
    start_text=await db.get_setting(bid,'text_start',f"👋 Assalomu alaykum {m.from_user.full_name}!\n\n🎬 Kino kodini yuboring yoki menyudan tanlang.")
    await m.answer(start_text, reply_markup=kino_user_menu(adminflag))
    if await db.get_setting(bid,'ad_start','0')=='1':
        await send_ad_to_user(m, bid)
@child_router.message(Command('panel'))
@child_router.message(F.text=='⚙️ Boshqaruv')
async def child_panel(m:Message):
    if not await is_child_admin(m): return await m.answer('⛔ Ruxsat yo‘q')
    remember_nav(m.from_user.id,'admin')
    await m.answer('🎬 Kino bot admin panel:', reply_markup=kino_admin_menu())
@child_router.message(F.text.in_({'🏠 Asosiy panel','◀️ Asosiy panel'}))
async def child_home(m:Message):
    remember_nav(m.from_user.id,'admin')
    await child_panel(m)

@child_router.message(F.text=='◀️ Orqaga')
async def child_back(m:Message):
    menu=parent_menu(nav_stack.get(m.from_user.id,'admin'))
    remember_nav(m.from_user.id, menu)
    if menu=='settings':
        return await m.answer('⚙️ Tizim sozlamalari bo‘limi:', reply_markup=settings_menu())
    if menu=='content':
        return await m.answer('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu())
    return await child_panel(m)

# ADMIN MENUS
@child_router.message(F.text=='🎬 Kontent boshqaruvi')
async def content(m:Message):
    if not await is_child_admin(m): return
    remember_nav(m.from_user.id,'content')
    await m.answer('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu())
@child_router.message(F.text=='⚙️ Tizim sozlamalari')
async def settings(m:Message):
    if not await is_child_admin(m): return
    remember_nav(m.from_user.id,'settings')
    await m.answer('⚙️ Tizim sozlamalari bo‘limi:', reply_markup=settings_menu())

# MOVIE ADD / SERIAL AUTO PARTS
@child_router.message(F.text=='📥 Kino yuklash')
async def add_movie_1(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(AddMovie.code)
    await m.answer('🎬 Kino kodini yuboring:\n\nMasalan: 1234')

@child_router.message(AddMovie.code)
async def add_movie_2(m:Message, state:FSMContext):
    bid=await runtime_db_id(m.bot.id)
    code=m.text.strip()
    old=await db.get_movie(bid, code)
    await state.update_data(code=code)
    if old:
        await state.update_data(existing_movie_id=old['id'], title=old['title'], premium=old['premium'], mode='choose')
        await state.set_state(AddMovie.action)
        return await m.answer(
            f"⚠️ Bu kod mavjud!\n\n🔑 Kod: {old['code']}\n🎬 Nomi: {old['title']}\n\nNima qilamiz?",
            reply_markup=movie_existing_menu()
        )
    await state.update_data(mode='new')
    await state.set_state(AddMovie.title)
    await m.answer('🎬 Kino nomini yuboring:')

@child_router.message(AddMovie.action)
async def add_movie_action(m:Message, state:FSMContext):
    txt=m.text.strip()
    if txt=='➕ Qism qo‘shish':
        await state.update_data(mode='add_part')
        await state.set_state(AddMovie.media)
        return await m.answer('📥 Yangi qism videosini/documentini yuboring.\n\nBot avtomatik keyingi raqamni beradi: 2-qism, 3-qism...')
    if txt=='✏️ Almashtirish':
        await state.update_data(mode='replace')
        await state.set_state(AddMovie.title)
        return await m.answer('✏️ Yangi kino nomini yuboring:')
    await state.clear()
    await m.answer('❌ Bekor qilindi.', reply_markup=content_menu())

@child_router.message(AddMovie.title)
async def add_movie_3(m:Message, state:FSMContext):
    await state.update_data(title=m.text.strip())
    await state.set_state(AddMovie.premium)
    await m.answer('💎 Bu kino premium bo‘ladimi?\n\nTanlang:', reply_markup=yes_no_premium_menu())

@child_router.message(AddMovie.premium)
async def add_movie_4(m:Message, state:FSMContext):
    txt=m.text.strip().lower()
    if 'bekor' in txt:
        await state.clear(); return await m.answer('❌ Bekor qilindi.', reply_markup=content_menu())
    premium=1 if txt.startswith('✅') or 'ha' in txt or txt in {'1','yes'} else 0
    await state.update_data(premium=premium)
    await state.set_state(AddMovie.media)
    await m.answer(('✅ Premium kino tanlandi.' if premium else '❌ Oddiy kino tanlandi.')+'\n\n📥 Kino videosini yoki documentini yuboring.')

@child_router.message(AddMovie.media)
async def add_movie_5(m:Message, state:FSMContext):
    data=await state.get_data(); file_id=None; cap=m.caption or ''
    if m.video: file_id=m.video.file_id
    elif m.document: file_id=m.document.file_id
    elif m.animation: file_id=m.animation.file_id
    elif m.audio: file_id=m.audio.file_id
    else: return await m.answer('❌ Video yoki document yuboring.')
    bid=await runtime_db_id(m.bot.id)
    mode=data.get('mode','new')
    code=data.get('code','').strip()

    if mode=='add_part':
        movie_id=int(data['existing_movie_id'])
        part_no=await db.next_part_no(movie_id)
        await db.add_part(movie_id, part_no, f'{part_no}-qism', file_id=file_id, caption=cap)
        await log_action(bid,m.from_user.id,'qism_qoshdi',f'{code} | {part_no}-qism')
        await state.clear()
        return await m.answer(f'✅ Qism qo‘shildi!\n\n🔑 Kod: {code}\n🎬 Qism: {part_no}-qism', reply_markup=content_menu())

    if mode=='replace':
        await db.delete_movie(bid, code)

    movie_id=await db.add_movie(bid, code, data.get('title',''), cap, data.get('premium',0))
    await db.add_part(movie_id, 1, '1-qism', file_id=file_id, caption=cap)
    await log_action(bid,m.from_user.id,'kino_qoshdi',code)
    await state.clear()
    await m.answer(f"✅ Kino saqlandi!\n\n🎬 Nomi: {data.get('title','')}\n🔑 Kod: {code}\n🎞 Qism: 1-qism\n💎 Premium: {'Ha' if data.get('premium',0) else 'Yo‘q'}", reply_markup=content_menu())
@child_router.message(F.text=='📋 Kinolar ro‘yxati')
async def movies_list(m:Message):
    if not await is_child_admin(m): return
    rows=await db.list_movies(await runtime_db_id(m.bot.id)); await m.answer('📋 Kinolar:\n'+'\n'.join([f"• {r['code']} — {r['title']} {'💎' if r['premium'] else ''} | 👁 {r['views']}" for r in rows]) if rows else '📭 Kino yo‘q')
@child_router.message(F.text=='🗑 Kino o‘chirish')
async def del_m1(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(DelMovie.code); await m.answer('🗑 O‘chirish uchun kino kodini yuboring:')
@child_router.message(DelMovie.code)
async def del_m2(m:Message, state:FSMContext):
    bid=await runtime_db_id(m.bot.id); await db.del_movie(bid, m.text.strip()); await log_action(bid,m.from_user.id,'kino_ochirdi',m.text.strip()); await state.clear(); await m.answer('✅ O‘chirildi', reply_markup=content_menu())
@child_router.message(F.text=='📝 Kino tahrirlash')
async def edit_m1(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(EditMovie.code)
    await m.answer('✏️ Tahrirlash uchun kino kodini yuboring:')

@child_router.message(EditMovie.code)
async def edit_m2(m:Message, state:FSMContext):
    bid=await runtime_db_id(m.bot.id)
    code=m.text.strip()
    mv=await db.get_movie(bid, code)
    if not mv:
        await state.clear()
        return await m.answer('❌ Kino topilmadi.', reply_markup=content_menu())
    await state.update_data(code=code, movie_id=mv['id'])
    await state.set_state(EditMovie.action)
    await m.answer(
        f"✏️ Kino tahrirlash\n\n🔑 Kod: {mv['code']}\n🎬 Nomi: {mv['title']}\n💎 Premium: {'✅ Ha' if mv['premium'] else '❌ Yo‘q'}\n\nNimani o‘zgartiramiz?",
        reply_markup=edit_movie_menu()
    )

@child_router.message(EditMovie.action)
async def edit_m3(m:Message, state:FSMContext):
    txt=m.text.strip()
    data=await state.get_data()
    bid=await runtime_db_id(m.bot.id)
    code=data.get('code','')
    if txt=='◀️ Orqaga':
        await state.clear(); return await m.answer('Bekor qilindi.', reply_markup=content_menu())
    if txt=='💎 Premium holatini o‘zgartirish':
        new=await db.toggle_movie_premium(bid, code)
        await log_action(bid,m.from_user.id,'kino_premium_ozgardi',code)
        await state.clear()
        return await m.answer('❌ Kino topilmadi' if new is None else f"✅ Premium holati: {'YOQILDI 💎' if new else 'O‘CHIRILDI'}", reply_markup=content_menu())
    if txt=='🎬 Kino nomini o‘zgartirish':
        await state.update_data(field='title')
        await state.set_state(EditMovie.value)
        return await m.answer('🎬 Yangi kino nomini yuboring:')
    if txt=='🔑 Kino kodini o‘zgartirish':
        await state.update_data(field='code')
        await state.set_state(EditMovie.value)
        return await m.answer('🔑 Yangi kino kodini yuboring:')
    await m.answer('Pastdagi tugmalardan birini tanlang.', reply_markup=edit_movie_menu())

@child_router.message(EditMovie.value)
async def edit_m4(m:Message, state:FSMContext):
    d=await state.get_data()
    bid=await runtime_db_id(m.bot.id)
    field=d.get('field')
    code=d.get('code')
    value=m.text.strip()
    if field=='title':
        await db.update_movie_field(bid, code, 'title', value)
        msg='✅ Kino nomi yangilandi.'
    elif field=='code':
        ok=await db.update_movie_code(bid, code, value)
        msg='✅ Kino kodi yangilandi.' if ok else '❌ Bu kod band yoki kino topilmadi.'
    else:
        msg='❌ Noto‘g‘ri amal.'
    await state.clear()
    await m.answer(msg, reply_markup=content_menu())

# CHANNELS
@child_router.message(F.text=='🔐 Kanallar')
async def ch_menu(m:Message):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    rows=await db.channels(bid)
    fake=await db.get_setting(bid,'sub_fake_verify','0')
    await m.answer(
        f'🔐 Majburiy obuna kanallari:\n\n'
        f'📊 Jami: {len(rows)} ta\n'
        f'🧪 Fake verify: {"✅ Yoniq" if fake=="1" else "❌ O‘chiq"}',
        reply_markup=channels_menu()
    )

@child_router.message(F.text=='➕ Kanal qo‘shish')
async def add_ch0(m:Message,state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(AddChannel.kind)
    await m.answer(
        '⚙️ Majburiy obuna turini tanlang:\n\n'
        'Quyida majburiy obunani qo‘shishning 3 ta turi mavjud:\n\n'
        '🔹 Ommaviy / Shaxsiy (Kanal · Guruh)\nHar qanday kanal yoki guruhni majburiy obunaga ulash.\n\n'
        '🔹 Shaxsiy / So‘rovli havola\nShaxsiy yoki so‘rovli kanal/guruhni post orqali ulash.\n\n'
        '🔹 Oddiy havola\nTelegramdan tashqari linklar: Instagram, sayt va boshqalar.',
        reply_markup=channel_type_menu(),
        link_preview_options=NO_PREVIEW
    )

@child_router.message(AddChannel.kind)
async def add_ch1(m:Message,state:FSMContext):
    txt=(m.text or '').strip()
    if txt=='◀️ Orqaga':
        await state.clear()
        return await ch_menu(m)

    checkable=0 if 'Oddiy' in txt else 1
    await state.update_data(kind=txt, checkable=checkable)

    if checkable:
        await state.set_state(AddChannel.title)
        return await m.answer(
            f'{txt} - ulash\n\n'
            'Kanal/guruhni ulash uchun quyidagilardan birini yuboring:\n\n'
            '1. Public kanal username: @kanal_nomi\n'
            '2. Kanal ID: -100xxxxxxxxxx\n'
            '3. Kanaldan bitta postni forward qiling\n\n'
            'Muhim: bot o‘sha kanal/guruhda admin bo‘lishi kerak.',
            reply_markup=rkb([['◀️ Orqaga']]),
            link_preview_options=NO_PREVIEW
        )

    await state.set_state(AddChannel.url)
    await state.update_data(title='Oddiy havola', chat='', checkable=0)
    return await m.answer(
        '🔗 Oddiy havola kiriting:\n\n'
        'Masalan: https://instagram.com/... yoki https://site.com\n\n'
        'Bu havola faqat ko‘rsatiladi, obuna tekshirilmaydi.',
        reply_markup=rkb([['◀️ Orqaga']]),
        link_preview_options=NO_PREVIEW
    )

@child_router.message(AddChannel.title)
async def add_ch2(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await ch_menu(m)

    sender = getattr(m, 'sender_chat', None)
    origin = getattr(m, 'forward_origin', None)
    origin_chat = getattr(origin, 'chat', None) if origin else None
    ch = sender or origin_chat

    if ch:
        title = ch.title or str(ch.id)
        chat = str(ch.id)
        url = ('https://t.me/' + ch.username) if getattr(ch, 'username', None) else ''
        await state.update_data(title=title, chat=chat, url=url, checkable=1)
        await state.set_state(AddChannel.url)
        return await m.answer(
            '✅ Kanal post orqali aniqlandi.\n\n'
            f'Kanal: {title}\n'
            f'ID: {chat}\n\n'
            'Endi kanal havolasini yuboring yoki skip yozing.',
            reply_markup=rkb([['skip'], ['◀️ Orqaga']]),
            link_preview_options=NO_PREVIEW
        )

    raw=(m.text or '').strip()
    chat, url = normalize_channel_input(raw)
    if not chat:
        return await m.answer('❌ @username, -100 ID yoki kanal postini yuboring.', link_preview_options=NO_PREVIEW)

    # Validate real Telegram subscription channel before saving.
    if not chat.startswith('http'):
        try:
            await m.bot.get_chat(chat)
        except Exception:
            return await m.answer(
                '❌ Kanal topilmadi yoki bot kanalga qo‘shilmagan.\n\n'
                'Tekshiring:\n'
                '1. Botni kanalga admin qiling\n'
                '2. Public kanal bo‘lsa @username yuboring\n'
                '3. Private kanal bo‘lsa kanaldan bitta postni forward qiling',
                link_preview_options=NO_PREVIEW
            )

    await state.update_data(title=(raw if raw.startswith('@') else (chat if chat.startswith('@') else raw)), chat=chat, url=url, checkable=1)
    await state.set_state(AddChannel.url)
    if url:
        return await m.answer(
            f'✅ Kanal aniqlandi: {chat}\n\n'
            'Havola ham tayyor. Saqlash uchun shu havolani qayta yuboring yoki skip yozing.',
            reply_markup=rkb([['skip'], ['◀️ Orqaga']]),
            link_preview_options=NO_PREVIEW
        )
    await m.answer('🔗 Kanal havolasini kiriting yoki skip yozing:', reply_markup=rkb([['skip'], ['◀️ Orqaga']]), link_preview_options=NO_PREVIEW)

@child_router.message(AddChannel.url)
async def add_ch4(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await ch_menu(m)

    d=await state.get_data()
    bid=await runtime_db_id(m.bot.id)
    checkable=int(d.get('checkable',1))

    url=(m.text or '').strip()
    if url.lower()=='skip':
        url=d.get('url','') or ''

    title=d.get('title') or url or 'Kanal'
    chat=d.get('chat') or url

    if not checkable:
        if not url.startswith(('http://','https://')):
            return await m.answer('❌ Oddiy havola http:// yoki https:// bilan boshlanishi kerak.', link_preview_options=NO_PREVIEW)
        chat=url

    if checkable:
        chat, auto_url = normalize_channel_input(chat)
        if not url:
            url = auto_url
        if chat.startswith('http'):
            await state.clear()
            return await m.answer(
                '❌ Bu havola orqali obunani tekshirib bo‘lmaydi.\n\n'
                'Private kanal bo‘lsa kanaldan bitta postni forward qiling yoki -100 ID yuboring.',
                reply_markup=channels_menu(),
                link_preview_options=NO_PREVIEW
            )
        try:
            me=await m.bot.get_me()
            member=await m.bot.get_chat_member(chat, me.id)
            if member.status not in {'administrator','creator'}:
                await state.clear()
                return await m.answer(
                    '❌ Bot bu kanalda admin emas.\n\n'
                    'Botni kanal/guruhga admin qiling, keyin qayta qo‘shing.',
                    reply_markup=channels_menu(),
                    link_preview_options=NO_PREVIEW
                )
        except Exception:
            await state.clear()
            return await m.answer(
                '❌ Kanalni tekshirib bo‘lmadi.\n\n'
                'Botni kanalga admin qiling yoki to‘g‘ri @username / -100 ID yuboring.',
                reply_markup=channels_menu(),
                link_preview_options=NO_PREVIEW
            )

    await db.add_channel(bid,title,chat,url,checkable)
    await state.clear()
    await m.answer(
        '✅ Kanal qo‘shildi va tekshiruvga tayyor!\n\n'
        f'📌 Nomi: {title}\n'
        f'🆔 Tekshiruv ID: {chat}\n'
        f'🔗 Havola: {url or "kiritilmagan"}',
        reply_markup=channels_menu(),
        link_preview_options=NO_PREVIEW
    )

@child_router.message(F.text=='📋 Ro‘yxatni ko‘rish')
async def ch_list(m:Message):
    rows=await db.channels(await runtime_db_id(m.bot.id))
    await m.answer('📋 Majburiy obuna kanallari ro‘yxati:\n\n'+'\n'.join([f"{r['id']}. {r['title']} | {'✅ tekshiradi' if r['checkable'] else '🌐 oddiy link'} | {r['url']}" for r in rows]) if rows else 'Kanal yo‘q', link_preview_options=NO_PREVIEW)
@child_router.message(F.text=='🗑 Kanalni o‘chirish')
async def del_ch1(m:Message,state:FSMContext): await state.set_state(DelChannel.id); await m.answer('🗑 Kanal ID raqamini yuboring:')
@child_router.message(DelChannel.id)
async def del_ch2(m:Message,state:FSMContext): await db.delete_channel(int(m.text.strip())); await state.clear(); await m.answer('✅ Kanal o‘chirildi', reply_markup=channels_menu())
@child_router.message(F.text=='🔐 Obuna statistikasi')
async def ch_stats(m:Message):
    if not await is_child_admin(m): return
    rows=await db.channels(await runtime_db_id(m.bot.id))
    if not rows: return await m.answer('Kanal yo‘q', reply_markup=channels_menu())
    txt='🔐 Obuna statistikasi:\n\n' + '\n'.join([f"• {r['title']} — {r['pass_count']} ta tekshiruvdan o‘tgan | {'✅ tekshiriladi' if r['checkable'] else '🌐 oddiy link'}" for r in rows])
    await m.answer(txt, reply_markup=channels_menu())

@child_router.message(F.text=='🔄 Fake verify ON/OFF')
async def sub_fake_toggle(m:Message):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    cur=await db.get_setting(bid,'sub_fake_verify','0')
    new='0' if cur=='1' else '1'
    await db.set_setting(bid,'sub_fake_verify',new)
    await m.answer(f"✅ Fake verify: {'Yoniq' if new=='1' else 'O‘chiq'}", reply_markup=channels_menu())

@child_router.callback_query(F.data=='check_sub')
async def check_sub(c:CallbackQuery):
    bid=await runtime_db_id(c.bot.id)
    ok, missing = await check_force_sub(c.bot, bid, c.from_user.id)
    if ok:
        await c.answer('✅ Obuna tasdiqlandi', show_alert=True)
        try:
            await c.message.edit_text('✅ Obuna tasdiqlandi!\n\nEndi kino kodini qayta yuboring.', reply_markup=None)
        except Exception:
            pass
        return

    await c.answer('❌ Hali barcha kanallarga obuna bo‘lmadingiz', show_alert=True)
    try:
        visible = await visible_force_channels(bid, missing)
        await c.message.edit_reply_markup(reply_markup=force_sub_inline(visible))
    except Exception:
        pass

# SETTINGS: ads admins texts pay premium antispam
@child_router.message(F.text=='📢 Reklama')
async def ads_panel(m:Message):
    remember_nav(m.from_user.id,'ads')
    bid=await runtime_db_id(m.bot.id); ads=await db.ads(bid); s=await db.get_setting(bid,'ad_start','0'); k=await db.get_setting(bid,'ad_movie','0')
    await m.answer(f"📢 Reklama bo‘limi\n\n📊 Jami reklamalar: {len(ads)} ta\n✅ Faol: {len([a for a in ads if a['active']])} ta\n👁 Jami ko‘rishlar: {sum([int(a['views'] or 0) for a in ads])} ta\n\n⚙️ Sozlamalar:\n🚀 Startda: {'✅ Yoniq' if s=='1' else '❌ O‘chiq'}\n🎬 Kino yuklaganda: {'✅ Yoniq' if k=='1' else '❌ O‘chiq'}", reply_markup=ads_menu(s=='1', k=='1'))

@child_router.message(F.text.startswith('🚀 Start:'))
async def ad_toggle_start(m:Message):
    bid=await runtime_db_id(m.bot.id); new=await db.toggle_ad(bid,'start'); s=new; k=await db.get_setting(bid,'ad_movie','0')
    await m.answer(f"✅ Start reklama: {'Yoniq' if new=='1' else 'O‘chiq'}", reply_markup=ads_menu(s=='1', k=='1'))

@child_router.message(F.text.startswith('🎬 Kino:'))
async def ad_toggle_movie(m:Message):
    bid=await runtime_db_id(m.bot.id); new=await db.toggle_ad(bid,'movie'); k=new; s=await db.get_setting(bid,'ad_start','0')
    await m.answer(f"✅ Kino reklamasi: {'Yoniq' if new=='1' else 'O‘chiq'}", reply_markup=ads_menu(s=='1', k=='1'))

@child_router.message(F.text=='➕ Reklama qo‘shish')
async def ad_add1(m:Message,state:FSMContext):
    remember_nav(m.from_user.id,'ads')
    await state.set_state(AddAd.media)
    await state.update_data(buttons='')
    await m.answer('➕ Reklama postini yuboring:\n\n📌 Rasm, video yoki matn yuborish mumkin.', reply_markup=rkb([nav_row()]))

@child_router.message(AddAd.media)
async def ad_add_media(m:Message,state:FSMContext):
    if m.text in {'◀️ Orqaga','🏠 Asosiy panel'}:
        await state.clear(); return await ads_panel(m)
    media_type='text'; file_id=''; text=m.text or m.caption or ''
    if m.photo:
        media_type='photo'; file_id=m.photo[-1].file_id
    elif m.video:
        media_type='video'; file_id=m.video.file_id
    elif m.document:
        media_type='document'; file_id=m.document.file_id
    elif m.animation:
        media_type='animation'; file_id=m.animation.file_id
    data={'media_type':media_type,'file_id':file_id,'text':text,'title':(text[:30] if text else media_type),'buttons':''}
    await state.update_data(**data)
    await state.set_state(AddAd.confirm)
    await send_ad_preview(m, data, '👇 Reklama shunday ko‘rinadi.\n\nTugma qo‘shish yoki saqlashingiz mumkin.')

@child_router.message(F.text=='🎛 Tugma qo‘shish')
async def ad_button_prompt(m:Message,state:FSMContext):
    await state.set_state(AddAd.buttons)
    await m.answer('🎛 Tugmalarni kiriting:\n\n📌 Format:\n[Tugma nomi|https://havola.com]\n\n📋 Namuna:\n[Kanal|https://t.me/kanal][Sayt|https://sayt.uz]\n[YouTube|https://youtube.com]\n\n❗ Havola http/https yoki t.me bilan boshlanishi shart.', reply_markup=ad_buttons_edit_menu(), link_preview_options=NO_PREVIEW)

@child_router.message(AddAd.buttons)
async def ad_buttons_save(m:Message,state:FSMContext):
    if m.text=='🗑 Tugmalarni o‘chirish':
        await state.update_data(buttons='')
        d=await state.get_data()
        await state.set_state(AddAd.confirm)
        await m.answer('✅ Tugmalar o‘chirildi.')
        return await send_ad_preview(m, d, '👇 Reklama shunday ko‘rinadi.\n\nTugma qo‘shish yoki saqlashingiz mumkin.')
    if m.text in {'◀️ Orqaga','🏠 Asosiy panel'}:
        d=await state.get_data()
        await state.set_state(AddAd.confirm)
        return await send_ad_preview(m, d, 'Reklama saqlash menyusi:')
    await state.update_data(buttons=m.text or '')
    d=await state.get_data()
    await state.set_state(AddAd.confirm)
    await m.answer('✅ Tugmalar saqlandi!\n\n'+(m.text or ''), link_preview_options=NO_PREVIEW)
    await send_ad_preview(m, d, '👆 Reklama shunday ko‘rinadi.\n\n👁 Ko‘rishlar: 0 ta\n⚙️ Holat: ✅ Faol\n📅 Qo‘shilgan: hozir')

@child_router.message(F.text=='✅ Saqlash')
async def ad_save(m:Message,state:FSMContext):
    d=await state.get_data(); bid=await runtime_db_id(m.bot.id)
    if not d.get('media_type') and not d.get('text'):
        return await m.answer('❌ Avval reklama postini yuboring.', reply_markup=ads_menu())
    await db.add_ad(bid,d.get('title','Reklama'),d.get('text',''),0,d.get('media_type','text'),d.get('file_id',''),d.get('buttons',''))
    await state.clear(); s=await db.get_setting(bid,'ad_start','0'); k=await db.get_setting(bid,'ad_movie','0')
    await m.answer('✅ Reklama saqlandi!', reply_markup=ads_menu(s=='1', k=='1'))

@child_router.message(F.text=='🗑 Bekor qilish')
async def ad_cancel(m:Message,state:FSMContext):
    await state.clear(); await m.answer('❌ Reklama bekor qilindi.', reply_markup=ads_menu())

@child_router.message(F.text=='📋 Reklamalar ro‘yxati')
async def ad_list(m:Message):
    remember_nav(m.from_user.id,'ads')
    rows=await db.ads(await runtime_db_id(m.bot.id))
    txt='📋 Reklamalar ro‘yxati\n📊 Jami: '+str(len(rows))+' ta | Sahifa: 1 / 1\n\n'
    txt += '\n'.join([f"{r['id']}. {'✅' if r['active'] else '❌'} 👁 {r['views'] or 0} ta | {fmt_dt(r['created_at'] or int(time.time()))}" for r in rows]) if rows else 'Reklama yo‘q'
    await m.answer(txt, reply_markup=rkb([['➕ Qo‘shish'], nav_row()]))

@child_router.message(F.text=='➕ Qo‘shish')
async def ad_add_alias(m:Message,state:FSMContext):
    await ad_add1(m,state)

@child_router.message(F.text=='👮 Adminlar')
async def admins_panel(m:Message):
    if not await is_child_admin(m): return
    remember_nav(m.from_user.id,'admins')
    await m.answer('👮 Adminlar bo‘limidasiz:', reply_markup=admins_menu())
@child_router.message(F.text=='➕ Admin qo‘shish')
async def add_admin1(m:Message,state:FSMContext): await state.set_state(AddAdmin.user_id); await m.answer('👤 Admin user ID kiriting:')
@child_router.message(AddAdmin.user_id)
async def add_admin2(m:Message,state:FSMContext): await db.add_admin(await runtime_db_id(m.bot.id),int(m.text.strip())); await state.clear(); await m.answer('✅ Admin qo‘shildi', reply_markup=admins_menu())
@child_router.message(F.text=='➖ Adminni o‘chirish')
async def del_admin1(m:Message,state:FSMContext): await state.set_state(DelAdmin.user_id); await m.answer('👤 O‘chiriladigan admin ID kiriting:')
@child_router.message(DelAdmin.user_id)
async def del_admin2(m:Message,state:FSMContext): await db.del_admin(await runtime_db_id(m.bot.id),int(m.text.strip())); await state.clear(); await m.answer('✅ Admin o‘chirildi', reply_markup=admins_menu())
@child_router.message(F.text=='📋 Adminlar ro‘yxati')
async def admins_list(m:Message):
    rows=await db.admins(await runtime_db_id(m.bot.id)); await m.answer('👮 Adminlar:\n'+'\n'.join([str(r['user_id']) for r in rows]) if rows else 'Admin yo‘q')

@child_router.message(F.text=='↗️ Ulashish')
async def protect_panel(m:Message):
    remember_nav(m.from_user.id,'protect')
    await m.answer('↗️ Kontentni himoya qilish sozlamalari\n\nOddiy va premium foydalanuvchilarga forward/save ruxsatlarini boshqarish.', reply_markup=protect_menu())
@child_router.message(F.text=='📝 Matnlar')
async def texts_panel(m:Message):
    remember_nav(m.from_user.id,'texts')
    await m.answer('📝 O‘zgartirmoqchi bo‘lgan matnni tanlang:', reply_markup=texts_menu())
@child_router.message(F.text.in_({'👋 Start xabari','📢 Kanallar chiqadigan matn','➕ Obuna bo‘lish tugmasi','✅ Tekshirish tugmasi','🎬 Kino caption matni','↗️ Ulashish tugmasi','🔒 Premium kino xabari','💎 Premium tugmasi','🎬 Kino qismlari sarlavhasi','❌ Noto‘g‘ri kod xabari','💳 Qism nomi matni','🎬 Kino nomi matni'}))
async def set_text1(m:Message,state:FSMContext):
    key='text_'+m.text.split(' ',1)[1].replace(' ','_'); await state.set_state(SetText.value); await state.update_data(key=key); await m.answer('📝 Yangi matnni yuboring:')
@child_router.message(SetText.value)
async def set_text2(m:Message,state:FSMContext):
    d=await state.get_data(); await db.set_setting(await runtime_db_id(m.bot.id),d['key'],m.text); await state.clear(); await m.answer('✅ Matn saqlandi', reply_markup=texts_menu())

@child_router.message(F.text=='💳 To‘lov tizimlari')
async def pay_panel(m:Message):
    remember_nav(m.from_user.id,'pay')
    bid=await runtime_db_id(m.bot.id)
    rows=await db.pay_methods(bid)
    auto_enabled=await db.get_setting(bid,'payment_auto_enabled','0')
    manual_enabled=await db.get_setting(bid,'payment_manual_enabled','1')
    txt='💳 To‘lov tizimlari sozlamalari:\n\n'+_pay_setting_text(auto_enabled, manual_enabled)+'\n\nJami: '+str(len(rows))+' ta\n\n✅ Avtomat ham ishlashi mumkin\n✅ Admin tasdiq ham ishlashi mumkin\nAdmin qaysini xohlasa yoqib/o‘chiradi'
    if rows:
        txt+='\n\n'+'\n'.join([f"{r['id']}. {r['name']}" for r in rows])
    await m.answer(txt, reply_markup=pay_menu())

@child_router.message(F.text=='🤖 Avtomat to‘lov ON/OFF')
async def pay_auto_toggle(m:Message):
    bid=await runtime_db_id(m.bot.id)
    cur=await db.get_setting(bid,'payment_auto_enabled','0')
    new='0' if cur=='1' else '1'
    await db.set_setting(bid,'payment_auto_enabled',new)
    manual=await db.get_setting(bid,'payment_manual_enabled','1')
    await m.answer('✅ To‘lov sozlamasi yangilandi.\n\n'+_pay_setting_text(new, manual), reply_markup=pay_menu())

@child_router.message(F.text=='👨‍💼 Admin tasdiq ON/OFF')
async def pay_manual_toggle(m:Message):
    bid=await runtime_db_id(m.bot.id)
    cur=await db.get_setting(bid,'payment_manual_enabled','1')
    new='0' if cur=='1' else '1'
    await db.set_setting(bid,'payment_manual_enabled',new)
    auto=await db.get_setting(bid,'payment_auto_enabled','0')
    await m.answer('✅ To‘lov sozlamasi yangilandi.\n\n'+_pay_setting_text(auto, new), reply_markup=pay_menu())
@child_router.message(F.text=='💳 Karta raqamini sozlash')
async def pay_card_set1(m:Message,state:FSMContext):
    await state.set_state(AddPay.value)
    await state.update_data(name='Karta')
    await m.answer('💳 Karta raqamini yuboring.\n\nMasalan: 8600 0000 0000 0000\nKarta egasini ham yozishingiz mumkin.')

@child_router.message(F.text=='➕ To‘lov tizimi qo‘shish')
async def pay_add1(m:Message,state:FSMContext): await state.set_state(AddPay.name); await m.answer('💳 To‘lov tizimi nomini kiriting (Click, Payme, Karta...)')
@child_router.message(AddPay.name)
async def pay_add2(m:Message,state:FSMContext): await state.update_data(name=m.text.strip()); await state.set_state(AddPay.value); await m.answer('💳 Karta/hamyon/link yoki instruktsiyani kiriting:')
@child_router.message(AddPay.value)
async def pay_add3(m:Message,state:FSMContext):
    d=await state.get_data(); await db.upsert_pay_method(await runtime_db_id(m.bot.id),d['name'],m.text); await state.clear(); await m.answer('✅ To‘lov tizimi saqlandi', reply_markup=pay_menu())
@child_router.message(F.text=='📋 To‘lov tizimlari ro‘yxati')
async def pay_list(m:Message):
    rows=await db.pay_methods(await runtime_db_id(m.bot.id)); await m.answer('💳 To‘lovlar:\n'+'\n'.join([f"{r['id']}. {r['name']} — {r['value']}" for r in rows]) if rows else 'To‘lov tizimi yo‘q')


@child_router.message(F.text=='🗑 To‘lov tizimini o‘chirish')
async def pay_del1(m:Message,state:FSMContext):
    rows=await db.pay_methods(await runtime_db_id(m.bot.id))
    txt='🗑 O‘chiriladigan to‘lov tizimi ID raqamini yuboring:\n\n'
    txt += ('\n'.join([f"{r['id']}. {r['name']} — {r['value']}" for r in rows]) if rows else 'To‘lov tizimi yo‘q')
    await state.set_state(DelPay.id)
    await m.answer(txt, link_preview_options=NO_PREVIEW)

@child_router.message(DelPay.id)
async def pay_del2(m:Message,state:FSMContext):
    try:
        await db.delete_pay_method(await runtime_db_id(m.bot.id), int(m.text.strip()))
        await m.answer('✅ To‘lov tizimi o‘chirildi', reply_markup=pay_menu())
    except Exception:
        await m.answer('❌ ID noto‘g‘ri.', reply_markup=pay_menu())
    await state.clear()

# PREMIUM
@child_router.message(F.text=='⚙️ Premium')
async def premium_panel(m:Message):
    remember_nav(m.from_user.id,'premium')
    bid=await runtime_db_id(m.bot.id); enabled=await db.get_setting(bid,'premium_enabled','1'); plist=await db.premium_list(bid)
    await m.answer(f"⚙️ Premium sozlamalar bo‘limidasiz:\n\n🔹 Premium holati: {'✅ Faol' if enabled=='1' else '❌ O‘chiq'}\n👥 Jami Premium foydalanuvchilar: {len(plist)} ta\n\n📌 Premium sozlamalarini boshqaring.", reply_markup=premium_admin_menu())
@child_router.message(F.text=='💡 Holat o‘zgartirish')
async def premium_toggle(m:Message):
    bid=await runtime_db_id(m.bot.id); cur=await db.get_setting(bid,'premium_enabled','1'); new='0' if cur=='1' else '1'; await db.set_setting(bid,'premium_enabled',new); await m.answer(f"✅ Premium holati: {'Faol' if new=='1' else 'O‘chiq'}", reply_markup=premium_admin_menu())
@child_router.message(F.text=='📋 Premium tariflar')
async def tariff_panel(m:Message):
    rows=await db.tariffs(await runtime_db_id(m.bot.id)); txt='📋 Premium tariflar:\n'+'\n'.join([f"{r['id']}. {r['name']} — {r['days']} kun — {fmt_money(r['price'])} so‘m" for r in rows]) if rows else 'Tarif yo‘q'
    await m.answer(txt, reply_markup=tariff_manage_menu())
@child_router.message(F.text=='➕ Tarif qo‘shish')
async def tariff_add1(m:Message,state:FSMContext): await state.set_state(AddTariff.name); await m.answer('📦 Tarif nomini kiriting:')
@child_router.message(AddTariff.name)
async def tariff_add2(m:Message,state:FSMContext): await state.update_data(name=m.text); await state.set_state(AddTariff.days); await m.answer('📅 Necha kun? (1–3650)')
@child_router.message(AddTariff.days)
async def tariff_add3(m:Message,state:FSMContext):
    try: days=int(m.text.strip())
    except: return await m.answer('❌ Faqat raqam kiriting')
    await state.update_data(days=days); await state.set_state(AddTariff.price); await m.answer('💰 Narxni kiriting: 1000 dan 1000000 so‘mgacha')
@child_router.message(AddTariff.price)
async def tariff_add4(m:Message,state:FSMContext):
    try: price=int(m.text.strip())
    except: return await m.answer('❌ Faqat raqam kiriting')
    d=await state.get_data(); await db.add_tariff(await runtime_db_id(m.bot.id),d['name'],d['days'],price); await state.clear(); await m.answer('✅ Tarif qo‘shildi', reply_markup=premium_admin_menu())

@child_router.message(F.text=='✏️ Tarifni o‘zgartirish')
async def tariff_edit1(m:Message,state:FSMContext):
    await state.set_state(EditTariff.tariff_id); await m.answer('✏️ O‘zgartiriladigan tarif ID raqamini yuboring:')
@child_router.message(EditTariff.tariff_id)
async def tariff_edit2(m:Message,state:FSMContext):
    await state.update_data(tariff_id=int(m.text.strip())); await state.set_state(EditTariff.field)
    await m.answer('Qaysi joyini o‘zgartirasiz?', reply_markup=rkb([['📝 Nomi'],['📅 Kuni'],['💰 Narxi'],['◀️ Asosiy panel']]))
@child_router.message(EditTariff.field)
async def tariff_edit3(m:Message,state:FSMContext):
    mapping={'📝 Nomi':'name','📅 Kuni':'days','💰 Narxi':'price'}
    field=mapping.get(m.text.strip())
    if not field: await state.clear(); return await m.answer('Bekor qilindi', reply_markup=premium_admin_menu())
    await state.update_data(field=field); await state.set_state(EditTariff.value)
    await m.answer('Yangi qiymatni yuboring:')
@child_router.message(EditTariff.value)
async def tariff_edit4(m:Message,state:FSMContext):
    d=await state.get_data(); await db.update_tariff(int(d['tariff_id']), await runtime_db_id(m.bot.id), d['field'], m.text.strip()); await state.clear(); await m.answer('✅ Tarif yangilandi', reply_markup=premium_admin_menu())
@child_router.message(F.text=='🗑 Tarifni o‘chirish')
async def tariff_del1(m:Message,state:FSMContext):
    await state.set_state(DelTariff.id); await m.answer('🗑 O‘chiriladigan tarif ID raqamini yuboring:')
@child_router.message(DelTariff.id)
async def tariff_del2(m:Message,state:FSMContext):
    await db.del_tariff(int(m.text.strip()), await runtime_db_id(m.bot.id)); await state.clear(); await m.answer('✅ Tarif o‘chirildi', reply_markup=premium_admin_menu())
@child_router.message(F.text=='➕ Premium berish / Muddatni boshqarish')
async def grant1(m:Message,state:FSMContext): await state.set_state(GrantPremium.user_id); await m.answer('👤 User ID kiriting:')
@child_router.message(GrantPremium.user_id)
async def grant2(m:Message,state:FSMContext): await state.update_data(user_id=int(m.text.strip())); await state.set_state(GrantPremium.days); await m.answer('📅 Necha kun premium berilsin?')
@child_router.message(GrantPremium.days)
async def grant3(m:Message,state:FSMContext):
    d=await state.get_data(); bid=await runtime_db_id(m.bot.id); await db.grant_premium(bid,d['user_id'],int(m.text.strip())); await log_action(bid,m.from_user.id,'premium_berdi',str(d['user_id'])); await state.clear(); await m.answer('✅ Premium berildi', reply_markup=premium_admin_menu())
@child_router.message(F.text=='➖ Premium olib tashlash')
async def rem1(m:Message,state:FSMContext): await state.set_state(RemovePremium.user_id); await m.answer('👤 User ID kiriting:')
@child_router.message(RemovePremium.user_id)
async def rem2(m:Message,state:FSMContext): await db.remove_premium(await runtime_db_id(m.bot.id),int(m.text.strip())); await state.clear(); await m.answer('✅ Premium olib tashlandi', reply_markup=premium_admin_menu())
@child_router.message(F.text=='👥 Premium foydalanuvchilar ro‘yxati')
async def plist(m:Message):
    rows=await db.premium_list(await runtime_db_id(m.bot.id)); await m.answer('👥 Premiumlar:\n'+'\n'.join([f"{r['user_id']} — {max(0,(r['until_ts']-int(time.time()))//86400)} kun" for r in rows]) if rows else 'Premium user yo‘q')

# USER PREMIUM PAYMENT
@child_router.message(F.text.in_({'💎 Premium','💎 Premium olish'}))
async def user_premium(m:Message):
    bid=await runtime_db_id(m.bot.id); rows=await db.tariffs(bid, True)
    if not rows: return await m.answer('📭 Hozircha premium tariflar yo‘q.')
    await m.answer('💎 Premium tariflardan birini tanlang:', reply_markup=tariff_inline(rows))
@child_router.callback_query(F.data=='show_tariffs')
async def show_tariffs(c:CallbackQuery):
    bid=await runtime_db_id(c.bot.id)
    rows=await db.tariffs(bid, True)
    if not rows:
        await c.message.answer('📭 Hozircha premium tariflar yo‘q.')
    else:
        await c.message.answer('💎 Premium olish uchun tariflardan birini tanlang:', reply_markup=tariff_inline(rows))
    await c.answer()

@child_router.callback_query(F.data.startswith('buy_tariff:'))
async def buy_tariff(c:CallbackQuery):
    tid=int(c.data.split(':')[1])
    t=await db.tariff_by_id(tid)
    methods=await db.pay_methods(t['bot_id'])
    auto_enabled=(await db.get_setting(t['bot_id'],'payment_auto_enabled','0'))=='1'
    manual_enabled=(await db.get_setting(t['bot_id'],'payment_manual_enabled','1'))=='1'
    if not auto_enabled and not manual_enabled:
        return await c.message.answer('❌ To‘lov tizimi vaqtincha o‘chirilgan.')
    if manual_enabled and not methods and not auto_enabled:
        return await c.message.answer('❌ To‘lov tizimi hali qo‘shilmagan.')
    await c.message.answer(
        f"💎 Tarif: {t['name']}\n📅 Muddat: {t['days']} kun\n💰 Narx: {fmt_money(t['price'])} so‘m\n\nTo‘lov turini tanlang:",
        reply_markup=payment_options_inline(methods,tid,auto_enabled,manual_enabled)
    )
    await c.answer()

@child_router.callback_query(F.data.startswith('auto_pay:'))
async def auto_pay(c:CallbackQuery):
    _, tid, provider = c.data.split(':')
    t=await db.tariff_by_id(int(tid))
    if not t:
        return await c.answer('Tarif topilmadi', show_alert=True)
    if (await db.get_setting(t['bot_id'],'payment_auto_enabled','0'))!='1':
        return await c.answer('Avtomat to‘lov o‘chirilgan', show_alert=True)
    methods=await db.pay_methods(t['bot_id'])
    url=_find_auto_link(methods, provider)
    pid=await db.add_payment(t['bot_id'], c.from_user.id, int(t['price']), provider.upper()+' AUTO', 'waiting_auto', None, int(tid))
    if url:
        await c.message.answer(
            f"🤖 {provider.upper()} avtomat to‘lov\n\n📦 Tarif: {t['name']}\n📅 Muddat: {t['days']} kun\n💰 Summa: {fmt_money(t['price'])} so‘m\n🧾 Buyurtma ID: {pid}\n\nTo‘lovni tugma orqali amalga oshiring. To‘lov tasdiqlansa premium avtomatik yoqiladi.",
            reply_markup=auto_payment_link_inline(url)
        )
    else:
        await c.message.answer(
            f"🤖 {provider.upper()} avtomat to‘lov tanlandi.\n\n📦 Tarif: {t['name']}\n💰 Summa: {fmt_money(t['price'])} so‘m\n🧾 Buyurtma ID: {pid}\n\n⚠️ Avtomat to‘lov linki hali sozlanmagan. Admin to‘lov tizimlari bo‘limidan Payme/Click linkini qo‘shishi kerak."
        )
    await c.answer()
@child_router.callback_query(F.data.startswith('buy_ref:'))
async def buy_with_ref(c:CallbackQuery):
    tid=int(c.data.split(':')[1]); t=await db.tariff_by_id(tid)
    bal=await db.referral_balance(t['bot_id'], c.from_user.id)
    if bal < int(t['price']):
        return await c.answer(f"Referal balans yetarli emas. Sizda {fmt_money(bal)} so‘m. Tarif {fmt_money(t['price'])} so‘m. Referal va haqiqiy pul qo‘shilmaydi.", show_alert=True)
    ok=await db.take_referral_balance(t['bot_id'], c.from_user.id, int(t['price']))
    if not ok: return await c.answer('Referal balans yetarli emas', show_alert=True)
    until=await db.grant_premium(t['bot_id'], c.from_user.id, int(t['days']))
    await c.message.answer(f"✅ Premium referal balans orqali yoqildi!\n\n📦 Tarif: {t['name']}\n📅 Muddat: {t['days']} kun\n💰 Summa: {fmt_money(t['price'])} so‘m\n⏰ Tugash vaqti: {fmt_dt(until)}")
    await c.answer('Premium yoqildi')

@child_router.callback_query(F.data.startswith('pay_method:'))
async def pay_method(c:CallbackQuery,state:FSMContext):
    _,tid,mid=c.data.split(':'); t=await db.tariff_by_id(int(tid)); methods=await db.pay_methods(t['bot_id']); method=next((x for x in methods if x['id']==int(mid)),None)
    await state.set_state(BuyPremium.screenshot); await state.update_data(tariff_id=int(tid), method=method['name'], amount=t['price'], days=t['days'], tariff_name=t['name'])
    await c.message.answer(f"💳 {method['name']} orqali to‘lov qiling:\n\n{method['value']}\n\n💰 Summa: {fmt_money(t['price'])} so‘m\n📸 To‘lov chekini rasm qilib yuboring.", link_preview_options=NO_PREVIEW); await c.answer()
@child_router.message(BuyPremium.screenshot)
async def premium_check(m:Message,state:FSMContext):
    if not m.photo and not m.document: return await m.answer('❌ Chek rasmini yuboring.')
    d=await state.get_data(); bid=await runtime_db_id(m.bot.id); file_id=m.photo[-1].file_id if m.photo else m.document.file_id
    pid=await db.add_payment(bid,m.from_user.id,d['amount'],d['method'],'pending',file_id,d['tariff_id'])
    owner=await child_owner_by_runtime(m.bot.id)
    cap=f"🧾 Yangi premium to‘lov\n\n📦 Tarif: {d['tariff_name']}\n📅 Muddat: {d['days']} kun\n👤 User: {m.from_user.id}\n💰 Summa: {fmt_money(d['amount'])} so‘m\n💳 Usul: {d['method']}"
    try: await m.bot.send_photo(owner,file_id,caption=cap, reply_markup=payment_admin_inline(pid))
    except Exception: pass
    await state.clear(); await m.answer('⏳ Chek yuborildi. Status: Tekshiruvda. Admin tasdiqlagandan keyin premium yoqiladi.')
@child_router.callback_query(F.data.startswith('pay_ok:'))
async def pay_ok(c:CallbackQuery):
    pid=int(c.data.split(':')[1]); p=await db.payment_by_id(pid); t=await db.tariff_by_id(p['tariff_id']) if p and p['tariff_id'] else None
    if not p: return await c.answer('To‘lov topilmadi', show_alert=True)
    days=t['days'] if t else 1; name=t['name'] if t else 'Premium'
    await db.update_payment(pid,'approved'); until=await db.grant_premium(p['bot_id'],p['user_id'],days); await log_action(p['bot_id'],c.from_user.id,'tolov_tasdiqlandi',str(pid))
    txt=f"✅ To‘lov tasdiqlandi! #Tasdiqlandi\n\n📦 Tarif: {name}\n📅 Muddat: {days} kun\n💳 To‘lov tizimi: {p['method']}\n👤 Foydalanuvchi: {p['user_id']}\n💰 To‘lov summasi: {fmt_money(p['amount'])} so‘m\n\n⏰ Tugash vaqti: {fmt_dt(until)}"
    try: await c.message.edit_caption((c.message.caption or '')+'\n\n✅ Tasdiqlandi')
    except Exception: pass
    await c.bot.send_message(p['user_id'],txt); await c.answer('Tasdiqlandi')
@child_router.callback_query(F.data.startswith('pay_no:'))
async def pay_no(c:CallbackQuery):
    pid=int(c.data.split(':')[1]); p=await db.payment_by_id(pid); await db.update_payment(pid,'rejected')
    try: await c.message.edit_caption((c.message.caption or '')+'\n\n❌ Rad etildi')
    except Exception: pass
    if p: await c.bot.send_message(p['user_id'],'❌ To‘lov chekingiz rad etildi. Iltimos, to‘g‘ri chek yuboring.')
    await c.answer('Rad etildi')
@child_router.message(F.text=='🧾 Chek statusi')
async def payment_status(m:Message):
    rows=await db.payments(await runtime_db_id(m.bot.id),user_id=m.from_user.id)
    if not rows: return await m.answer('🧾 Sizda chek tarixi yo‘q.')
    mapper={'pending':'⏳ Tekshiruvda','approved':'✅ Tasdiqlandi','rejected':'❌ Rad etildi'}
    await m.answer('🧾 Chek statuslari:\n'+'\n'.join([f"#{r['id']} — {fmt_money(r['amount'])} so‘m — {mapper.get(r['status'],r['status'])}" for r in rows[:10]]))

# USER FEATURES
@child_router.message(F.text=='🎬 Kino kodini yozing')
async def code_prompt(m:Message): await m.answer('🎬 Kino kodini yozib yuboring:')
@child_router.message(F.text=='🔍 Kino qidiruv')
async def search1(m:Message,state:FSMContext): await m.answer('🎬 Kino olish uchun kino kodini yozing.')
@child_router.message(SearchMovie.query)
async def search2(m:Message,state:FSMContext):
    rows=await db.search_movies(await runtime_db_id(m.bot.id),m.text,20); await state.clear()
    await m.answer('🔍 Natijalar:\n'+'\n'.join([f"• {r['title']} — kod: {r['code']} {'💎' if r['premium'] else ''}" for r in rows]) if rows else '❌ Hech narsa topilmadi')
@child_router.message(F.text=='🆕 Yangi kinolar')
async def latest(m:Message):
    rows=await db.latest_movies(await runtime_db_id(m.bot.id),20); await m.answer('🆕 Yangi kinolar:\n'+'\n'.join([f"• {r['title']} — kod: {r['code']}" for r in rows]) if rows else 'Kino yo‘q')
@child_router.message(F.text=='🔥 TOP kinolar')
async def top(m:Message):
    rows=await db.top_movies(await runtime_db_id(m.bot.id),20); await m.answer('🔥 Eng ko‘p ko‘rilganlar:\n'+'\n'.join([f"• {r['title']} — kod: {r['code']} | 👁 {r['views']}" for r in rows]) if rows else 'Kino yo‘q')
@child_router.message(F.text=='❤️ Sevimlilar')
async def favs(m:Message):
    rows=await db.favorites(await runtime_db_id(m.bot.id),m.from_user.id); await m.answer('❤️ Sevimlilar:\n'+'\n'.join([f"• {r['title']} — kod: {r['code']}" for r in rows]) if rows else 'Sevimlilar bo‘sh')
@child_router.callback_query(F.data.startswith('fav:'))
async def fav_toggle(c:CallbackQuery):
    added=await db.toggle_fav(await runtime_db_id(c.bot.id),c.from_user.id,int(c.data.split(':')[1])); await c.answer('❤️ Qo‘shildi' if added else '💔 Olib tashlandi', show_alert=True)
@child_router.message(F.text=='📥 Kino so‘rov qilish')
async def req1(m:Message,state:FSMContext): await state.set_state(RequestMovie.text); await m.answer('📥 Qaysi kinoni qo‘shish kerak? Nomini yozing:')
@child_router.message(RequestMovie.text)
async def req2(m:Message,state:FSMContext):
    bid=await runtime_db_id(m.bot.id); await db.add_request(bid,m.from_user.id,m.text); owner=await child_owner_by_runtime(m.bot.id)
    try: await m.bot.send_message(owner,f"📥 Yangi kino so‘rov\n👤 User: {m.from_user.id}\n🎬 Kino: {m.text}")
    except Exception: pass
    await state.clear(); await m.answer('✅ So‘rovingiz adminga yuborildi.')
@child_router.message(F.text=='📥 So‘rovlar')
async def reqs(m:Message):
    if not await is_child_admin(m): return
    rows=await db.requests(await runtime_db_id(m.bot.id)); await m.answer('📥 So‘rovlar:\n'+'\n'.join([f"#{r['id']} | {r['user_id']} | {r['text']} | {r['status']}" for r in rows]) if rows else 'So‘rov yo‘q')

@child_router.message(F.text=='🗣 Referal')
async def child_referral(m:Message):
    bid=await runtime_db_id(m.bot.id)
    me=await m.bot.get_me()
    bonus=int(await db.get_setting(bid,'referral_bonus','0') or 0)
    bal=await db.referral_balance(bid,m.from_user.id)
    refs=await db.child_ref_count(bid,m.from_user.id)
    await m.answer(
        f'🗣 Referal bo‘limi\n\n'
        f'👥 Takliflaringiz: {refs} ta\n'
        f'🎁 Har referal bonusi: {fmt_money(bonus)} so‘m\n'
        f'💼 Referal balans: {fmt_money(bal)} so‘m\n\n'
        '❗ Referal balans faqat premium tarifga ishlaydi. Haqiqiy pul bilan qo‘shilmaydi.\n\n'
        f'🔗 Havolangiz:\nhttps://t.me/{me.username}?start={m.from_user.id}'
    )

@child_router.message(F.text=='🎁 Referal sozlamalari')
async def referral_settings_panel(m:Message):
    if not await is_child_admin(m): return
    remember_nav(m.from_user.id,'referral')
    bid=await runtime_db_id(m.bot.id); bonus=await db.get_setting(bid,'referral_bonus','0')
    await m.answer(f'🎁 Referal sozlamalari\n\nHozirgi bonus: {fmt_money(bonus)} so‘m', reply_markup=referral_admin_menu())

@child_router.message(F.text=='🎁 Referal bonus summasi')
async def referral_bonus1(m:Message,state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(ReferralSetting.bonus)
    await m.answer('🎁 Har bir taklif uchun referal bonus summasini kiriting. Masalan: 200')

@child_router.message(F.text=='📋 Referal sozlamalari')
async def referral_settings_list(m:Message):
    bid=await runtime_db_id(m.bot.id); bonus=await db.get_setting(bid,'referral_bonus','0')
    await m.answer(f'📋 Referal sozlamalari\n\n🎁 Bonus: {fmt_money(bonus)} so‘m\n❗ Bu balans faqat premium tarifga ishlaydi.')

@child_router.message(ReferralSetting.bonus)
async def referral_bonus2(m:Message,state:FSMContext):
    await db.set_setting(await runtime_db_id(m.bot.id),'referral_bonus',max(0,int(m.text.strip())))
    await state.clear(); await m.answer('✅ Referal bonus saqlandi', reply_markup=settings_menu())

# ANTISPAM
async def spam_allowed(bot_id:int,user_id:int):
    if await db.get_setting(bot_id,'antispam_enabled','1')!='1': return True,0
    now=time.time(); key=(bot_id,user_id); rec=spam_cache.get(key,{'times':[],'blocked_until':0})
    if rec.get('blocked_until',0)>now: return False,int(rec['blocked_until']-now)
    limit=int(await db.get_setting(bot_id,'antispam_limit','5')); window=int(await db.get_setting(bot_id,'antispam_window','3')); block=int(await db.get_setting(bot_id,'antispam_block','10'))
    rec['times']=[x for x in rec.get('times',[]) if now-x<=window]; rec['times'].append(now)
    if len(rec['times'])>limit:
        rec['blocked_until']=now+block; spam_cache[key]=rec; return False,block
    spam_cache[key]=rec; return True,0
@child_router.message(F.text=='🛡 Anti-spam')
async def spam_panel(m:Message):
    remember_nav(m.from_user.id,'antispam')
    bid=await runtime_db_id(m.bot.id); en=await db.get_setting(bid,'antispam_enabled','1'); lim=await db.get_setting(bid,'antispam_limit','5'); win=await db.get_setting(bid,'antispam_window','3'); bl=await db.get_setting(bid,'antispam_block','10')
    await m.answer(f"🛡 Anti-spam\n\nHolat: {'✅ Yoniq' if en=='1' else '❌ O‘chiq'}\nLimit: {lim} ta / {win} sekund\nBlok: {bl} sekund", reply_markup=antispam_menu())
@child_router.message(F.text=='🛡 Anti-spam ON/OFF')
async def spam_toggle(m:Message):
    bid=await runtime_db_id(m.bot.id); cur=await db.get_setting(bid,'antispam_enabled','1'); new='0' if cur=='1' else '1'; await db.set_setting(bid,'antispam_enabled',new); await m.answer(f"✅ Anti-spam: {'Yoniq' if new=='1' else 'O‘chiq'}", reply_markup=antispam_menu())
@child_router.message(F.text=='⚡ Limit sozlash')
async def spam_limit1(m:Message,state:FSMContext): await state.set_state(AntiSpamSettings.limit); await m.answer('⚡ Limitni kiriting. Masalan: 5')
@child_router.message(AntiSpamSettings.limit)
async def spam_limit2(m:Message,state:FSMContext): await db.set_setting(await runtime_db_id(m.bot.id),'antispam_limit',int(m.text.strip())); await state.clear(); await m.answer('✅ Limit saqlandi', reply_markup=antispam_menu())
@child_router.message(F.text=='⏱ Blok vaqtini sozlash')
async def spam_block1(m:Message,state:FSMContext): await state.set_state(AntiSpamSettings.block); await m.answer('⏱ Blok vaqtini sekundda kiriting. Masalan: 10')
@child_router.message(AntiSpamSettings.block)
async def spam_block2(m:Message,state:FSMContext): await db.set_setting(await runtime_db_id(m.bot.id),'antispam_block',int(m.text.strip())); await state.clear(); await m.answer('✅ Blok vaqti saqlandi', reply_markup=antispam_menu())



@child_router.message(F.text=='🗑 DB tozalash')
async def db_clean_panel(m:Message):
    if not await is_child_admin(m):
        return
    bid=await runtime_db_id(m.bot.id)
    deleted=await db.db_cleanup(bid, 30)
    await m.answer(
        "🗑 DB tozalash bajarildi!\n\n"
        "Muhim ma’lumotlar o‘chmadi: botlar, balans, kinolar, premium tariflar saqlandi.\n\n"
        f"🧾 Eski cheklar: {deleted.get('main_topups',0)} ta\n"
        f"📢 Eski reklama yetkazish yozuvlari: {deleted.get('ad_deliveries',0)} ta\n"
        f"💎 Eskirgan premium: {deleted.get('expired_premium',0)} ta\n"
        f"⚙️ Runtime yozuvlar: {deleted.get('runtime_events',0)} ta",
        reply_markup=settings_menu()
    )

@child_router.message(F.text=='🧹 Kesh tozalash')
async def cache_panel(m:Message):
    if not await is_child_admin(m): return
    remember_nav(m.from_user.id,'cache')
    await m.answer('🧹 Kesh tozalash bo‘limi\n\nBu yerda vaqtinchalik state/spam/runtime keshlarni tozalaysiz. Botni qayta ishga tushirmasdan “qotib qolgan” user holatlarini tiklashga yordam beradi.', reply_markup=cache_menu())

@child_router.message(F.text.in_({'🧹 Keshni tozalash','♻️ State/spam cache tozalash'}))
async def cache_clear(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    spam_cache.clear()
    runtime_cache.clear()
    deleted=await db.clean_expired_premium(bid)
    await state.clear()
    await m.answer(f'✅ Kesh tozalandi\n\n🧹 Spam/state cache: tozalandi\n♻️ Runtime cache: tozalandi\n💎 Eskirgan premiumlar: {deleted} ta o‘chirildi', reply_markup=settings_menu())

# STATS LOG BROADCAST REMINDERS
@child_router.message(F.text=='📊 Statistika')
async def child_stats(m:Message):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    now=int(time.time())
    movies=len(await db.list_movies(bid)); prem=len(await db.premium_list(bid)); pays=len(await db.payments(bid)); req=len(await db.requests(bid))
    views_all=await db.movie_view_count(bid)
    views_24=await db.movie_view_count(bid, now-86400)
    views_7=await db.movie_view_count(bid, now-7*86400)
    views_30=await db.movie_view_count(bid, now-30*86400)
    pay_sum=await db.payments_sum(bid,'approved')
    ref_sum=await db.referral_total(bid)
    chs=await db.channel_stats(bid)
    ads=await db.ads_total_views(bid)
    top=await db.top_movies(bid,5)
    top_txt='\n'.join([f"{i+1}. {r['title'] or r['code']} — 👁 {r['views']}" for i,r in enumerate(top)]) or 'Hali ko‘rishlar yo‘q'
    await m.answer(
        f"📊 Statistika PRO\n\n"
        f"🎬 Kinolar: {movies} ta\n"
        f"👥 Aktiv userlar: {await db.child_user_count(bid)} ta\n"
        f"👁 Ko‘rishlar: {views_all} ta\n"
        f"├ 24 soat: {views_24}\n├ 7 kun: {views_7}\n└ 30 kun: {views_30}\n\n"
        f"💎 Premiumlar: {prem} ta\n"
        f"💳 To‘lovlar: {pays} ta | ✅ {fmt_money(pay_sum['s'])} so‘m\n"
        f"🎁 Referal balanslar: {fmt_money(ref_sum['s'])} so‘m / {ref_sum['c']} user\n"
        f"🔐 Obuna kanallari: {chs['c']} ta | ✅ tekshiruv: {chs['p']}\n"
        f"📢 Reklamalar: {ads['c']} ta | 👁 {ads['v']}\n"
        f"📥 So‘rovlar: {req} ta\n\n"
        f"🔥 TOP 5:\n{top_txt}",
        reply_markup=kino_admin_menu()
    )

@child_router.message(F.text=='👥 Foydalanuvchilar')
async def child_users_panel(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    st=await db.child_users_stats(bid)
    await m.answer(
        "👥 Foydalanuvchilar bo‘limi\n\n"
        f"📊 Jami: {st['total']} ta\n"
        f"🟢 24 soat aktiv: {st['active24']} ta\n"
        f"🟢 7 kun aktiv: {st['active7']} ta\n"
        f"💎 Premium: {st['premium']} ta\n"
        f"🚫 Bloklangan: {st['blocked']} ta\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=rkb([
            ['📋 Foydalanuvchilar ro‘yxati'],
            ['🔎 Foydalanuvchi qidirish'],
            ['🚫 Bloklangan foydalanuvchilar'],
            nav_row(),
        ])
    )

@child_router.message(F.text=='📋 Foydalanuvchilar ro‘yxati')
async def child_users_list(m:Message):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id)
    rows=await db.child_users_list(bid, 30)
    if not rows:
        return await m.answer('📋 Hali foydalanuvchilar yo‘q.', reply_markup=kino_admin_menu())
    txt='📋 Oxirgi foydalanuvchilar:\\n\\n'
    for r in rows:
        txt += f"👤 {r['user_id']} | 👁 {r['views']} | 🕒 {fmt_dt(r['last_seen'])}\\n"
    await m.answer(txt, reply_markup=rkb([['🔎 Foydalanuvchi qidirish'], nav_row()]))

@child_router.message(F.text=='🔎 Foydalanuvchi qidirish')
@child_router.message(F.text=='🔍 Foydalanuvchi qidirish')
async def child_user_search1(m:Message, state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state('child_user_search')
    await m.answer('🔎 Foydalanuvchi ID raqamini yuboring:', reply_markup=rkb([['◀️ Orqaga']]))

@child_router.message(StateFilter('child_user_search'))
async def child_user_search2(m:Message, state:FSMContext):
    if m.text=='◀️ Orqaga':
        await state.clear()
        return await child_users_panel(m,state)
    raw=(m.text or '').strip()
    if not raw.isdigit():
        return await m.answer('❌ Faqat raqam ID yuboring.')
    bid=await runtime_db_id(m.bot.id)
    info=await db.child_user_search(bid, int(raw))
    prem='Yo‘q'
    if int(info['premium_until'] or 0) > int(time.time()):
        prem='Bor, tugashi: '+fmt_dt(info['premium_until'])
    await state.clear()
    await m.answer(
        f"👤 User ID: {info['user_id']}\\n"
        f"👁 Ko‘rishlar: {info['views']} ta\\n"
        f"🕒 Oxirgi aktiv: {fmt_dt(info['last_seen']) if info['last_seen'] else 'yo‘q'}\\n"
        f"💎 Premium: {prem}",
        reply_markup=rkb([['🔎 Foydalanuvchi qidirish'], nav_row()])
    )

@child_router.message(F.text=='🚫 Bloklangan foydalanuvchilar')
async def child_blocked_users(m:Message):
    if not await is_child_admin(m): return
    await m.answer('🚫 Bloklangan foydalanuvchilar hozircha yo‘q.\\n\\nKeyingi versiyada block/unblock qo‘shiladi.', reply_markup=rkb([nav_row()]))


@child_router.message(F.text=='👮 Admin log')
async def admin_logs(m:Message):
    if not await is_child_admin(m): return
    rows=await db.logs(await runtime_db_id(m.bot.id)); await m.answer('👮 Admin log:\n'+'\n'.join([f"{fmt_dt(r['created_at'])} | {r['admin_id']} | {r['action']} | {r['details']}" for r in rows]) if rows else 'Log yo‘q')
@child_router.message(F.text=='📩 Xabar yuborish')
async def broadcast1(m:Message,state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(Broadcast.text); await m.answer('📩 Yuboriladigan xabar matnini kiriting:')
@child_router.message(Broadcast.text)
async def broadcast2(m:Message,state:FSMContext):
    await state.update_data(text=m.text); await state.set_state(Broadcast.confirm); await m.answer('📢 Preview:\n\n'+m.text+'\n\nYuborishni boshlaymizmi?', reply_markup=broadcast_confirm_menu())
@child_router.message(Broadcast.confirm)
async def broadcast3(m:Message,state:FSMContext):
    if m.text.strip()=='🔘 Tugma qo‘shish':
        return await m.answer('🔘 Tugma formatini shu tarzda yozing:\n[Tugma matni|Tugma linki]\n\nMisol:\n[Instagram|instagram.com]')
    if m.text.strip()!='✅ Boshlash': await state.clear(); return await m.answer('❌ Bekor qilindi', reply_markup=kino_admin_menu())
    d=await state.get_data(); await state.clear(); await m.answer('✅ Xabar yuborish boshlandi. Katta bazada flood limitdan saqlanish uchun sekin yuboriladi.', reply_markup=kino_admin_menu())
@child_router.message(F.text.in_({'⚡ Avtomatik to‘lov tizimlari','📝 Oddiy to‘lov tizimlari','👥 Oddiy (🔒 Ruxsat berish)','🌟 Premium (🔒 Ruxsat berish)'}))
async def child_stubs(m:Message): await m.answer('✅ Bo‘lim tayyor. Kerakli sozlamalarni yuqoridagi tugmalardan boshqaring.')



async def send_ad_preview(m:Message, data:dict, text_prefix='👆 Reklama shunday ko‘rinadi.'):
    markup=ad_buttons_markup(data.get('buttons',''))
    text=data.get('text','') or ''
    mt=data.get('media_type','text')
    fid=data.get('file_id','')
    try:
        if mt=='photo' and fid:
            await m.answer_photo(fid, caption=text, reply_markup=markup)
        elif mt=='video' and fid:
            await m.answer_video(fid, caption=text, reply_markup=markup)
        elif mt=='document' and fid:
            await m.answer_document(fid, caption=text, reply_markup=markup)
        elif mt=='animation' and fid:
            await m.answer_animation(fid, caption=text, reply_markup=markup)
        else:
            await m.answer(text or '📢 Reklama', reply_markup=markup, link_preview_options=NO_PREVIEW)
    except Exception:
        await m.answer(text or '📢 Reklama', reply_markup=markup, link_preview_options=NO_PREVIEW)
    await m.answer(text_prefix, reply_markup=ad_confirm_menu(), link_preview_options=NO_PREVIEW)


def ad_buttons_markup(raw:str):
    if not raw: return None
    rows=[]
    for line in raw.splitlines():
        buttons=[]
        for name,url in re.findall(r'\[([^\]|]+)\|([^\]]+)\]', line):
            url=url.strip()
            if url.startswith('t.me/'): url='https://'+url
            if url.startswith('@'): url='https://t.me/'+url.lstrip('@')
            if not (url.startswith('http://') or url.startswith('https://')): continue
            buttons.append(InlineKeyboardButton(text=name.strip(), url=url))
        if buttons: rows.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None

async def send_ad_to_user(m:Message, bot_id:int):
    ad=await db.active_ad(bot_id)
    if not ad: return
    markup=ad_buttons_markup(ad['buttons'] if 'buttons' in ad.keys() else '')
    text=ad['text'] or ''
    mt=ad['media_type'] if 'media_type' in ad.keys() else ''
    fid=ad['file_id'] if 'file_id' in ad.keys() else ''
    try:
        if mt=='photo' and fid:
            await m.answer_photo(fid, caption=text, reply_markup=markup)
        elif mt=='video' and fid:
            await m.answer_video(fid, caption=text, reply_markup=markup)
        elif mt=='document' and fid:
            await m.answer_document(fid, caption=text, reply_markup=markup)
        elif mt=='animation' and fid:
            await m.answer_animation(fid, caption=text, reply_markup=markup)
        else:
            await m.answer(text or '📢 Reklama', reply_markup=markup, link_preview_options=NO_PREVIEW)
        await db.inc_ad_view(ad['id'])
        try: await db.record_ad_delivery(bot_id, m.from_user.id, ad['id'])
        except Exception: pass
    except Exception as e:
        log.warning('ad send failed: %s', e)
        try: await db.record_runtime_event(bot_id, 'warning', 'ad_send_failed', str(e))
        except Exception: pass

async def send_part_message(m:Message, mv, p):
    bid=await runtime_db_id(m.bot.id)
    cap=p['caption'] or mv['caption'] or await db.get_setting(bid,'text_Kino_caption_matni','')
    if p['file_id']:
        await m.answer_video(p['file_id'], caption=cap, protect_content=True, reply_markup=movie_inline(mv['id']))
    if await db.get_setting(bid,'ad_movie','0')=='1':
        interval=int(await db.get_setting(bid,'ad_movie_interval','3') or 3)
        if await db.should_send_movie_ad(bid, m.from_user.id, interval):
            await send_ad_to_user(m, bid)

async def send_movie(m:Message, mv):
    bid=await runtime_db_id(m.bot.id); rows=await db.parts(mv['id'])
    if not rows: return await m.answer('❌ Kino fayli topilmadi.')
    await db.inc_view(bid,mv['id'],m.from_user.id)
    if len(rows)==1:
        return await send_part_message(m, mv, rows[0])
    txt='🎬 Kino qismlari ro‘yxati:\n\n' + '\n'.join([f"{p['part_no']}. {p['part_no']}-qism {'⭐💎' if mv['premium'] else ''}" for p in rows])
    await m.answer(txt, reply_markup=movie_parts_inline(rows, bool(mv['premium'])))

@child_router.callback_query(F.data.startswith('movie_part:'))
async def movie_part_callback(c:CallbackQuery):
    part_id=int(c.data.split(':')[1])
    p=await db.part_by_id(part_id)
    if not p: return await c.answer('Qism topilmadi', show_alert=True)
    mv=await db.movie_by_id(p['movie_id'])
    if not mv: return await c.answer('Kino topilmadi', show_alert=True)
    bid=await runtime_db_id(c.bot.id)
    if mv['premium'] and not await db.has_premium(bid,c.from_user.id):
        return await c.message.answer(await db.get_setting(bid,'text_Premium_kino_xabari','🔒 Bu kino premium. Ko‘rish uchun 💎 Premium olish tugmasini bosing.'), reply_markup=premium_locked_inline())
    await send_part_message(c.message, mv, p)
    await c.answer()

@child_router.message(F.text)
async def movie_code(m:Message):
    if m.text in {'🎬 Kino kodini yozing'}: return await m.answer('🎬 Kino kodini yozib yuboring:')
    bid=await runtime_db_id(m.bot.id)
    limit_ok, used, limit, limit_status, grace_until = await db.smart_limit_check(bid)
    if limit_status in {'slow_grace_started', 'slow'}:
        owner=await child_owner_by_runtime(m.bot.id)
        if limit_status=='slow_grace_started':
            try:
                await m.bot.send_message(
                    owner,
                    f"⚠️ Bot kunlik limitdan oshdi!\n\n"
                    f"📊 Bugungi foydalanuvchi: {fmt_money(used)} / {fmt_money(limit)}\n"
                    f"⏳ Bot to‘xtamaydi, 24 soat sekin rejimda ishlaydi.\n"
                    f"📦 Tarifni oshirsangiz tezlik normal bo‘ladi."
                )
            except Exception:
                pass
        await asyncio.sleep(2)
    elif not limit_ok:
        owner=await child_owner_by_runtime(m.bot.id)
        try:
            await m.bot.send_message(
                owner,
                f"⛔ Bot cheklangan!\n\n"
                f"📊 Limit: {fmt_money(used)} / {fmt_money(limit)}\n"
                f"Sabab: tarif muddati tugagan yoki grace period yakunlangan.\n"
                f"📦 Asosiy bot → Botlarim → Tarifni oshirish."
            )
        except Exception:
            pass
        return await m.answer('⛔ Bot hozir cheklangan. Bot egasi tarifni oshirgandan keyin avtomatik ishlaydi.')
    ok,wait=await spam_allowed(bid,m.from_user.id)
    if not ok: return await m.answer(f'⛔ Juda tez-tez yuboryapsiz! Iltimos {wait} soniya kuting...')
    ok_sub, not_join = await check_force_sub(m.bot, bid, m.from_user.id)
    if not ok_sub:
        visible = await visible_force_channels(bid, not_join)
        if not visible:
            return await m.answer(
                '🔐 Majburiy obuna sozlangan, lekin kanal havolasi topilmadi.\n\n'
                'Admin kanal qo‘shganda @username yoki kanal havolasini kiritishi kerak.',
                link_preview_options=NO_PREVIEW
            )
        return await m.answer(
            '🔐 Kino olish uchun quyidagi kanallarga obuna bo‘ling.\n\n'
            'Obuna bo‘lgach ✅ Tekshirish tugmasini bosing.',
            reply_markup=force_sub_inline(visible),
            link_preview_options=NO_PREVIEW
        )
    mv=await db.get_movie(bid, m.text.strip())
    if not mv: return await m.answer(await db.get_setting(bid,'text_Noto‘g‘ri_kod_xabari','❌ Bunday kod topilmadi.'))
    if mv['premium'] and not await db.has_premium(bid,m.from_user.id): return await m.answer(await db.get_setting(bid,'text_Premium_kino_xabari','🔒 Bu kino premium. Ko‘rish uchun 💎 Premium olish tugmasini bosing.'), reply_markup=premium_locked_inline())
    await send_movie(m,mv)

async def background_worker(bot:Bot, bot_id:int):
    while True:
        try:
            for p in await db.premium_due_reminders(bot_id):
                await bot.send_message(p['user_id'],'⏰ Premium muddati 1 kundan keyin tugaydi. Davom ettirish uchun 💎 Premium bo‘limidan tarif oling.')
                await db.mark_reminded(bot_id,p['user_id'])
            for ad in await db.scheduled_ads(bot_id):
                owner=await child_owner_by_runtime(bot.id)
                try: await bot.send_message(owner,'📅 Rejalangan reklama vaqti keldi:\n\n'+ad['text'])
                except Exception: pass
                await db.mark_ad_sent(ad['id'])
        except Exception as e: log.warning('bg worker: %s',e)
        await asyncio.sleep(60)

async def start_child(bot_id:int):
    """
    Har bir child bot alohida polling task bo‘lib ishlaydi.
    MUHIM: aiogram Router bitta Dispatcherga ulanadi. Shuning uchun har child uchun
    child_router deepcopy qilinadi. Aks holda 2-bot ishlamay qoladi.
    """
    bot_id=int(bot_id)
    old=child_tasks.get(bot_id)
    if old and not old.done():
        return True

    r=await db.bot_by_id(bot_id)
    if not r:
        return False
    if r['status']!='active':
        return False

    ok, used, limit, _ = await db.platform_limit_ok(bot_id)
    if not ok:
        await db.auto_pause_limit(bot_id, 'expired_or_limit')
        try:
            await db.record_runtime_event(bot_id, 'warning', 'child_not_started', 'platform expired or limit reached')
        except Exception:
            pass
        return False

    async def runner():
        bot=None
        bg=None
        username=str(r['username'] or bot_id)
        try:
            bot=Bot(r['token'])

            # Tokenni oldindan tekshiramiz
            me=await bot.get_me()
            username=me.username or username

            # Har bir child bot uchun mustaqil Dispatcher + mustaqil Router copy.
            dp=Dispatcher(storage=MemoryStorage())
            dp.include_router(copy.deepcopy(child_router))

            log.info('Child bot started @%s id=%s', username, bot_id)
            try:
                await db.record_runtime_event(bot_id, 'info', 'child_started', f'@{username}')
            except Exception:
                pass

            bg=asyncio.create_task(background_worker(bot,bot_id))

            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                pass

            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

        except TelegramConflictError as e:
            log.error('Child bot conflict @%s: %s', username, e)
            try:
                await db.record_runtime_event(bot_id, 'error', 'telegram_conflict', str(e))
            except Exception:
                pass
            # Conflict bo‘lsa statusni active qoldiramiz, manager keyin qayta urinadi.
            await asyncio.sleep(5)

        except asyncio.CancelledError:
            log.info('Child bot stopped @%s id=%s', username, bot_id)
            raise

        except Exception as e:
            log.exception('Child bot crashed @%s id=%s', username, bot_id)
            try:
                await db.record_runtime_event(bot_id, 'error', 'child_crash', str(e))
            except Exception:
                pass

        finally:
            if bg:
                bg.cancel()
            if bot:
                try:
                    await bot.session.close()
                except Exception:
                    pass

    child_tasks[bot_id]=asyncio.create_task(runner())
    return True

async def stop_child(bot_id:int):
    bot_id=int(bot_id)
    t=child_tasks.get(bot_id)
    if t and not t.done():
        t.cancel()
        try:
            await t
        except Exception:
            pass
    child_tasks.pop(bot_id, None)
    return True

async def start_all_children():
    rows=await db.bots()
    started=0
    for r in rows:
        try:
            if r['status']=='active':
                ok=await start_child(int(r['id']))
                if ok:
                    started+=1
        except Exception as e:
            log.warning('start_all_children failed for %s: %s', r['id'], e)
    log.info('Child manager started %s active bots', started)
    return started

async def child_manager_worker():
    """
    Har 30 sekundda DBdagi active botlarni tekshiradi.
    Yangi bot yaratilsa yoki task yiqilsa avtomatik qayta ishga tushiradi.
    """
    while True:
        try:
            rows=await db.bots()
            active_ids=set()
            for r in rows:
                bot_id=int(r['id'])
                if r['status']=='active':
                    active_ids.add(bot_id)
                    t=child_tasks.get(bot_id)
                    if not t or t.done():
                        await start_child(bot_id)
                else:
                    t=child_tasks.get(bot_id)
                    if t and not t.done():
                        await stop_child(bot_id)

            # DBda yo‘q yoki active emas bo‘lgan eski tasklarni to‘xtatamiz
            for bot_id in list(child_tasks.keys()):
                if bot_id not in active_ids:
                    await stop_child(bot_id)

        except Exception as e:
            log.warning('child_manager_worker error: %s', e)

        await asyncio.sleep(30)

async def broadcast_worker():
    """Reklama/xabarlarni navbat bilan yuboradi, Telegram limitdan saqlaydi."""
    while True:
        if not broadcast_queue:
            await asyncio.sleep(1)
            continue
        bot, user_id, text = broadcast_queue.pop(0)
        try:
            await bot.send_message(user_id, text)
        except Exception:
            pass
        await asyncio.sleep(0.07)

async def start_all_active_children():
    return await start_all_children()


async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN env kerak')
    await db.init_db()
    await db.ensure_platform_tables()
    await start_all_children()
    asyncio.create_task(child_manager_worker())
    asyncio.create_task(broadcast_worker())
    bot=Bot(BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage()); dp.include_router(main_router)
    log.info('%s started', BOT_NAME)
    try:
        try: await bot.delete_webhook(drop_pending_updates=True)
        except Exception: pass
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except TelegramConflictError as e:
        log.error('MAIN BOT CONFLICT: %s', e)
        await db.record_runtime_event(0, 'error', 'main_telegram_conflict', str(e))
        raise
    finally: await bot.session.close()
if __name__=='__main__': asyncio.run(main())