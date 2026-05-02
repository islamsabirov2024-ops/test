import asyncio, logging, time, re, datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from . import db
from .config import BOT_TOKEN, SUPER_ADMIN_ID, BOT_NAME, SUBSCRIPTION_FAKE_VERIFY
from .keyboards import *
from .states import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
log=logging.getLogger(__name__)
child_tasks={}; runtime_cache={}; spam_cache={}
NO_PREVIEW=LinkPreviewOptions(is_disabled=True)
main_router=Router(); child_router=Router()

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
    price=int(await db.get_global('create_price','0') or 0)
    await state.update_data(kind='kino')
    await m.answer(
        "🎬 Kino Bot\n\n"
        "Ushbu tizim orqali siz kinolarni botga yuklaysiz va ularga maxsus kod biriktirasiz. "
        "Foydalanuvchilar shu kod orqali kinoni tez va oson ko‘rishadi.\n\n"
        "Bot ichida statistika, majburiy obuna, reklama, premium, tariflar, chek tasdiqlash, "
        "TOP kinolar, yangi kinolar, sevimlilar, premium, reklama va referal tizimi mavjud.\n\n"
        f"💵 Yaratish narxi: {fmt_money(price)} so‘m\n"
        "🎁 Boshlang‘ich bonus: admin sozlaydi\n\n"
        "Davom etish uchun pastdagi tugmani bosing.",
        reply_markup=create_kino_menu(price)
    )

@main_router.message(F.text.startswith('✅ Bot yaratish'))
async def create_kino_confirm(m:Message, state:FSMContext):
    price=int(await db.get_global('create_price','0') or 0)
    u=await db.get_user(m.from_user.id)
    bal=int(u['balance']) if u else 0
    if price > 0 and bal < price:
        return await m.answer(f'❌ Balans yetarli emas. Kerak: {fmt_money(price)} so‘m\nSizda: {fmt_money(bal)} so‘m', reply_markup=main_menu())
    await state.set_state(CreateBot.token)
    await state.update_data(kind='kino', price=price)
    await m.answer('🤖 BotFather’dan olingan bot tokenni yuboring:')

@main_router.message(F.text.in_({'🚀 Nakrutka Bot','💵 Pul Bot','📥 OpenBudget Bot','🛍 Mahsulot Bot','🔐 VipKanal Bot','🚀 Smm Bot [💎 PREMIUM]','🎥 ProKino Bot [💎 PREMIUM]'}))
async def other_bot_type(m:Message):
    await m.answer('⏳ Bu bot turi keyingi versiyada ulanadi. Hozir 100% ishlaydigan tayyor template: 🎬 Kino Bot.', reply_markup=bot_types_menu())

@main_router.message(CreateBot.token)
async def create_bot_token(m:Message, state:FSMContext):
    data=await state.get_data(); token=m.text.strip(); price=int(data.get('price',0) or 0)
    try:
        b=Bot(token); me=await b.get_me(); await b.session.close()
    except Exception as e: return await m.answer(f'❌ Token xato: {e}')
    try:
        if price > 0:
            paid=await db.take_balance(m.from_user.id, price)
            if not paid: return await m.answer('❌ Balans yetarli emas.', reply_markup=main_menu())
        bot_id=await db.add_bot(m.from_user.id, token, me.username or '', me.full_name or 'Kino Bot')
        await db.add_tariff(bot_id,'1 kunlik Premium',1,1000); await db.add_tariff(bot_id,'3 kunlik Premium',3,5000); await db.add_tariff(bot_id,'7 kunlik Premium',7,10000)
        await db.add_pay_method(bot_id,'Karta','Karta raqamini admin paneldan kiriting')
        await db.set_setting(bot_id,'premium_enabled','1'); await db.set_setting(bot_id,'text_Premium_kino_xabari','🔒 Bu kino premium. Ko‘rish uchun 💎 Premium olish tugmasini bosing.'); await db.set_setting(bot_id,'antispam_enabled','1'); await db.set_setting(bot_id,'antispam_limit','5'); await db.set_setting(bot_id,'antispam_window','3'); await db.set_setting(bot_id,'antispam_block','10')
        await start_child(bot_id)
        await m.answer(f'✅ Kino Bot yaratildi: @{me.username}\n🆔 ID: {bot_id}\n\nBotga kiring va /panel bosing.', reply_markup=main_menu())
    except Exception as e: await m.answer(f'❌ Saqlashda xato: {e}')
    await state.clear()
@main_router.message(F.text=='🤖 Botlarim')
async def my_bots(m:Message):
    rows=await db.bots(m.from_user.id)
    if not rows: return await m.answer('📭 Sizda bot yo‘q. ➕ Bot yaratish ni bosing.')
    await m.answer('🤖 Botlaringiz:')
    for r in rows: await m.answer(f"🆔 {r['id']} | @{r['username']} | {r['status']}", reply_markup=bot_actions(r['id'], r['status']))
@main_router.callback_query(F.data.startswith('bot_toggle:'))
async def bot_toggle(c:CallbackQuery):
    bot_id=int(c.data.split(':')[1]); r=await db.bot_by_id(bot_id)
    if not r or (r['owner_id']!=c.from_user.id and not is_admin(c.from_user.id)):
        return await c.answer('Ruxsat yo‘q', show_alert=True)
    new='paused' if r['status']=='active' else 'active'
    await db.set_bot_status(bot_id,new)
    try:
        if new=='active':
            await start_child(bot_id)
            txt=f"✅ @{r['username']} holati: active\n\n🟢 Bot yoqildi."
        else:
            await stop_child(bot_id)
            txt=f"✅ @{r['username']} holati: paused\n\n🔴 Bot to‘xtatildi."
        await c.message.edit_text(txt, reply_markup=bot_actions(bot_id,new))
    except Exception:
        await c.message.answer(f"✅ @{r['username']} holati: {new}", reply_markup=bot_actions(bot_id,new))
    await c.answer('Bajarildi')
@main_router.callback_query(F.data.startswith('bot_delete:'))
async def bot_delete(c:CallbackQuery): await c.answer('Xavfsizlik uchun repo versiyada faqat pauza mavjud. O‘chirishni DB backupdan keyin qiling.', show_alert=True)

@main_router.callback_query(F.data.startswith('bot_token:'))
async def bot_token_change(c:CallbackQuery, state:FSMContext):
    bot_id=int(c.data.split(':')[1]); r=await db.bot_by_id(bot_id)
    if not r or (r['owner_id']!=c.from_user.id and not is_admin(c.from_user.id)): return await c.answer('Ruxsat yo‘q', show_alert=True)
    await state.set_state(ChangeBotToken.token); await state.update_data(bot_id=bot_id)
    await c.message.answer('🔑 Yangi bot tokenini yuboring:'); await c.answer()

@main_router.message(ChangeBotToken.token)
async def bot_token_save(m:Message, state:FSMContext):
    data=await state.get_data(); bot_id=int(data['bot_id']); token=m.text.strip()
    try:
        b=Bot(token); me=await b.get_me(); await b.session.close()
    except Exception as e: return await m.answer(f'❌ Token xato: {e}')
    await stop_child(bot_id)
    # SQLite uchun sodda update
    async with db.conn() as con:
        await con.execute('UPDATE bots SET token=?, username=?, title=? WHERE id=?',(token,me.username or '',me.full_name or 'Kino Bot',bot_id)); await con.commit()
    runtime_cache.clear(); await start_child(bot_id); await state.clear()
    await m.answer(f'✅ Token almashtirildi: @{me.username}', reply_markup=main_menu())

@main_router.message(F.text=='🗣 Referal')
async def referral(m:Message):
    bonus=int(await db.get_global('referral_bonus','0') or 0); refs=await db.ref_count(m.from_user.id)
    me=await m.bot.get_me(); link=f'https://t.me/{me.username}?start={m.from_user.id}'
    await m.answer(f'🗣 Referal bo‘limi\n\n👥 Referallaringiz: {refs} ta\n🎁 Har referal bonusi: {fmt_money(bonus)} so‘m\n\n🔗 Sizning linkingiz:\n{link}')

@main_router.message(F.text=='💳 Hisob to\'ldirish')
async def topup(m:Message):
    await m.answer('💳 To‘lov tizimini tanlang:\n\nPayme/Click/Karta/Humo orqali balans to‘ldirish admin tasdiqlashi bilan ishlaydi.', reply_markup=topup_menu())

@main_router.message(F.text.in_({'⚪ Payme (Avto)','🔵 Click (Avto)','💳 Karta (Avto)','💳 Humo'}))
async def topup_stub(m:Message):
    await m.answer('🧾 Hozircha balans to‘ldirish manual rejimda. Admin bilan bog‘laning: 📩 Murojaat', reply_markup=main_menu())

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

@main_router.message(F.text=='📱 Shaxsiy kabinet')
async def cabinet(m:Message):
    u=await db.get_user(m.from_user.id); refs=await db.ref_count(m.from_user.id)
    await m.answer(f"🪪 ID: {m.from_user.id}\n├ 💼 Balansingiz: {fmt_money(u['balance'] if u else 0)} so‘m\n├ 👥 Referallaringiz: {refs} ta\n├ 🤖 Botlaringiz: {len(await db.bots(m.from_user.id))} ta\n└ 💰 Kiritgan pullaringiz: 0 so‘m")
@main_router.message(F.text=='📊 Umumiy statistika')
async def stats(m:Message):
    if not is_admin(m.from_user.id): return
    s=await db.stat(); await m.answer(f"📊 Umumiy statistika\n\n👥 Users: {s['users']}\n🤖 Botlar: {s['bots']}\n🎬 Kinolar: {s['movies']}\n💳 To‘lovlar: {s['payments']}")
@main_router.message(F.text=='🤖 Barcha botlar')
async def allbots(m:Message):
    if not is_admin(m.from_user.id): return
    rows=await db.bots(); await m.answer('🤖 Barcha botlar:\n'+'\n'.join([f"{r['id']}. @{r['username']} | owner {r['owner_id']} | {r['status']}" for r in rows]) if rows else 'Bot yo‘q')
@main_router.message(F.text)
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
    ad_start=await db.get_setting(bid,'ad_start','0')
    if ad_start=='1':
        ads=await db.ads(bid)
        if ads: start_text+='\n\n📢 '+ads[0]['text']
    await m.answer(start_text, reply_markup=kino_user_menu(adminflag))
@child_router.message(Command('panel'))
@child_router.message(F.text=='⚙️ Boshqaruv')
async def child_panel(m:Message):
    if not await is_child_admin(m): return await m.answer('⛔ Ruxsat yo‘q')
    await m.answer('🎬 Kino bot admin panel:', reply_markup=kino_admin_menu())
@child_router.message(F.text.in_({'◀️ Orqaga','◀️ Asosiy panel'}))
async def child_back(m:Message): await child_panel(m)

# ADMIN MENUS
@child_router.message(F.text=='🎬 Kontent boshqaruvi')
async def content(m:Message):
    if not await is_child_admin(m): return
    await m.answer('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu())
@child_router.message(F.text=='⚙️ Tizim sozlamalari')
async def settings(m:Message):
    if not await is_child_admin(m): return
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
    rows=await db.channels(await runtime_db_id(m.bot.id))
    await m.answer(f'🔐 Majburiy obuna kanallari:\n\n📊 Jami: {len(rows)} ta', reply_markup=channels_menu())

@child_router.message(F.text=='➕ Kanal qo‘shish')
async def add_ch0(m:Message,state:FSMContext):
    if not await is_child_admin(m): return
    await state.set_state(AddChannel.kind)
    await m.answer(
        '⚙️ Majburiy obuna turini tanlang:\n\n'
        'Quyida majburiy obunani qo‘shishning 3 ta turi mavjud:\n\n'
        '🔹 Ommaviy / Shaxsiy (Kanal · Guruh)\nHar qanday kanal yoki guruhni majburiy obunaga ulash.\n\n'
        '🔹 Shaxsiy / So‘rovli havola\nShaxsiy yoki so‘rovli havola orqali o‘tganlarni kuzatish.\n\n'
        '🔹 Oddiy havola\nTelegramdan tashqari linklar: Instagram, sayt va boshqalar.',
        reply_markup=channel_type_menu()
    )

@child_router.message(AddChannel.kind)
async def add_ch1(m:Message,state:FSMContext):
    txt=m.text.strip()
    if txt=='◀️ Orqaga':
        await state.clear(); return await ch_menu(m)
    checkable=0 if 'Oddiy' in txt else 1
    await state.update_data(kind=txt, checkable=checkable)
    if checkable:
        await state.set_state(AddChannel.title)
        return await m.answer(
            f'{txt} - ulash\n\n'
            'Quyida kanal/guruhni ulashning 3 ta oddiy usuli mavjud:\n\n'
            '🔹 1. ID orqali ulash\nKanal yoki guruh ID raqamini kiriting. ID odatda -100... shaklida bo‘ladi.\n\n'
            '🔹 2. Havola orqali ulash\nKanal/guruh havolasini yuboring. Masalan: @kanal_nomi yoki t.me/kanal\n\n'
            '🔹 3. Postni ulash orqali\nKanal yoki guruhdan bitta postni ushbu botga yuboring.',
            reply_markup=rkb([['◀️ Orqaga']])
        )
    await state.set_state(AddChannel.url)
    await state.update_data(title='Oddiy havola', chat='')
    return await m.answer('🔗 Havola kiriting:\n\nMasalan: site.com yoki t.me/kanal', reply_markup=rkb([['◀️ Orqaga']]))

@child_router.message(AddChannel.title)
async def add_ch2(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga': await state.clear(); return await ch_menu(m)
    if not m.text:
        sender = getattr(m, 'sender_chat', None)
        origin = getattr(m, 'forward_origin', None)
        origin_chat = getattr(origin, 'chat', None) if origin else None
        ch = sender or origin_chat
        if ch:
            title = ch.title or str(ch.id)
            chat = str(ch.id)
            url = ('https://t.me/' + ch.username) if getattr(ch, 'username', None) else ''
            await state.update_data(title=title, chat=chat, url=url)
            await state.set_state(AddChannel.url)
            return await m.answer('✅ Kanal post orqali aniqlandi. Havolasini yuboring yoki “skip” yozing:', link_preview_options=NO_PREVIEW)
        return await m.answer('❌ Kanal ID, @username, havola yoki kanal postini yuboring.')
    raw=m.text.strip()
    title=raw; chat=raw; url=raw if raw.startswith('http') else ('https://t.me/'+raw.lstrip('@') if raw.startswith('@') else '')
    await state.update_data(title=title, chat=chat, url=url)
    await state.set_state(AddChannel.url)
    await m.answer('🔗 Kanal havolasini kiriting yoki shu havolani tasdiqlash uchun qayta yuboring:')

@child_router.message(AddChannel.url)
async def add_ch4(m:Message,state:FSMContext):
    if m.text=='◀️ Orqaga': await state.clear(); return await ch_menu(m)
    d=await state.get_data(); bid=await runtime_db_id(m.bot.id)
    url=m.text.strip()
    if url.lower()=='skip':
        url=d.get('url','')
    title=d.get('title') or url
    chat=d.get('chat') or url
    checkable=int(d.get('checkable',1))
    if checkable and url.startswith('@'):
        chat=url
        url='https://t.me/'+url.lstrip('@')
    await db.add_channel(bid,title,chat,url,checkable)
    await state.clear(); await m.answer('✅ Kanal qo‘shildi', reply_markup=channels_menu())

@child_router.message(F.text=='📋 Ro‘yxatni ko‘rish')
async def ch_list(m:Message):
    rows=await db.channels(await runtime_db_id(m.bot.id))
    await m.answer('📋 Majburiy obuna kanallari ro‘yxati:\n\n'+'\n'.join([f"{r['id']}. {r['title']} | {'✅ tekshiradi' if r['checkable'] else '🌐 oddiy link'} | {r['url']}" for r in rows]) if rows else 'Kanal yo‘q')
@child_router.message(F.text=='🗑 Kanalni o‘chirish')
async def del_ch1(m:Message,state:FSMContext): await state.set_state(DelChannel.id); await m.answer('🗑 Kanal ID raqamini yuboring:')
@child_router.message(DelChannel.id)
async def del_ch2(m:Message,state:FSMContext): await db.delete_channel(int(m.text.strip())); await state.clear(); await m.answer('✅ Kanal o‘chirildi', reply_markup=channels_menu())
@child_router.message(F.text=='🔐 Obuna statistikasi')
async def ch_stats(m:Message):
    rows=await db.channels(await runtime_db_id(m.bot.id)); await m.answer('🔐 Obuna statistikasi:\n'+'\n'.join([f"• {r['title']}: {r['pass_count']} ta tekshiruvdan o‘tgan" for r in rows]) if rows else 'Kanal yo‘q')
@child_router.callback_query(F.data=='check_sub')
async def check_sub(c:CallbackQuery):
    bid=await runtime_db_id(c.bot.id); ok=True; chans=await db.channels(bid)
    for ch in chans:
        if not ch['checkable']: continue
        try:
            member=await c.bot.get_chat_member(ch['chat_id'], c.from_user.id)
            if member.status in {'left','kicked'}: ok=False
            else: await db.channel_pass(ch['id'])
        except Exception: ok=False
    await c.answer('✅ Obuna tasdiqlandi' if ok or SUBSCRIPTION_FAKE_VERIFY else '❌ Hali obuna bo‘lmadingiz', show_alert=True)

# SETTINGS: ads admins texts pay premium antispam
@child_router.message(F.text=='📢 Reklama')
async def ads_panel(m:Message):
    bid=await runtime_db_id(m.bot.id); ads=await db.ads(bid); s=await db.get_setting(bid,'ad_start','0'); k=await db.get_setting(bid,'ad_movie','0')
    await m.answer(f"📢 Reklama bo‘limi\n\n📊 Jami reklamalar: {len(ads)} ta\n🚀 Start: {'✅ Yoniq' if s=='1' else '❌ O‘chiq'}\n🎬 Kino: {'✅ Yoniq' if k=='1' else '❌ O‘chiq'}", reply_markup=ads_menu())
@child_router.message(F.text.in_({'🚀 Start: almashtirish','🎬 Kino: almashtirish'}))
async def ad_toggle(m:Message):
    field='start' if m.text.startswith('🚀') else 'movie'; new=await db.toggle_ad(await runtime_db_id(m.bot.id),field); await m.answer(f"✅ Reklama {field}: {'Yoniq' if new=='1' else 'O‘chiq'}", reply_markup=ads_menu())
@child_router.message(F.text.in_({'➕ Reklama qo‘shish','📅 Reklama rejalash'}))
async def ad_add1(m:Message,state:FSMContext): await state.set_state(AddAd.title); await state.update_data(schedule_mode=1 if m.text.startswith('📅') else 0); await m.answer('📢 Reklama sarlavhasini kiriting:')
@child_router.message(AddAd.title)
async def ad_add2(m:Message,state:FSMContext): await state.update_data(title=m.text); await state.set_state(AddAd.text); await m.answer('📢 Reklama matnini yuboring:')
@child_router.message(AddAd.text)
async def ad_add3(m:Message,state:FSMContext):
    d=await state.get_data(); await state.update_data(text=m.text)
    if d.get('schedule_mode'): await state.set_state(AddAd.schedule); return await m.answer('⏰ Qachon yuborilsin? Masalan: 2026-05-02 20:00 yoki 30 minut yoki 2 soat')
    await db.add_ad(await runtime_db_id(m.bot.id),d['title'],m.text,0); await state.clear(); await m.answer('✅ Reklama qo‘shildi', reply_markup=ads_menu())
@child_router.message(AddAd.schedule)
async def ad_add4(m:Message,state:FSMContext):
    d=await state.get_data(); ts=parse_schedule(m.text); await db.add_ad(await runtime_db_id(m.bot.id),d['title'],d['text'],ts); await state.clear(); await m.answer('✅ Reklama rejalandi', reply_markup=ads_menu())
@child_router.message(F.text=='📋 Reklamalar ro‘yxati')
async def ad_list(m:Message):
    rows=await db.ads(await runtime_db_id(m.bot.id)); await m.answer('📋 Reklamalar:\n'+'\n'.join([f"{r['id']}. {r['title']} | {'⏰ '+fmt_dt(r['scheduled_at']) if r['scheduled_at'] else 'oddiy'} | sent:{r['sent']}" for r in rows]) if rows else 'Reklama yo‘q')
@child_router.message(F.text=='📢 Reklama preview')
async def ad_preview(m:Message):
    rows=await db.ads(await runtime_db_id(m.bot.id)); await m.answer('📢 Preview:\n\n'+(rows[0]['text'] if rows else 'Reklama yo‘q'))

@child_router.message(F.text=='👮 Adminlar')
async def admins_panel(m:Message):
    if not await is_child_admin(m): return
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
async def protect_panel(m:Message): await m.answer('↗️ Kontentni himoya qilish sozlamalari\n\nOddiy va premium foydalanuvchilarga forward/save ruxsatlarini boshqarish.', reply_markup=protect_menu())
@child_router.message(F.text=='📝 Matnlar')
async def texts_panel(m:Message): await m.answer('📝 O‘zgartirmoqchi bo‘lgan matnni tanlang:', reply_markup=texts_menu())
@child_router.message(F.text.in_({'👋 Start xabari','📢 Kanallar chiqadigan matn','➕ Obuna bo‘lish tugmasi','✅ Tekshirish tugmasi','🎬 Kino caption matni','↗️ Ulashish tugmasi','🔒 Premium kino xabari','💎 Premium tugmasi','🎬 Kino qismlari sarlavhasi','❌ Noto‘g‘ri kod xabari','💳 Qism nomi matni','🎬 Kino nomi matni'}))
async def set_text1(m:Message,state:FSMContext):
    key='text_'+m.text.split(' ',1)[1].replace(' ','_'); await state.set_state(SetText.value); await state.update_data(key=key); await m.answer('📝 Yangi matnni yuboring:')
@child_router.message(SetText.value)
async def set_text2(m:Message,state:FSMContext):
    d=await state.get_data(); await db.set_setting(await runtime_db_id(m.bot.id),d['key'],m.text); await state.clear(); await m.answer('✅ Matn saqlandi', reply_markup=texts_menu())

@child_router.message(F.text=='💳 To‘lov tizimlari')
async def pay_panel(m:Message):
    rows=await db.pay_methods(await runtime_db_id(m.bot.id))
    txt='💳 To‘lov tizimlari sozlamalari:\n\nJami: '+str(len(rows))+' ta'
    if rows:
        txt+='\n\n'+'\n'.join([f"{r['id']}. {r['name']}" for r in rows])
    await m.answer(txt, reply_markup=pay_menu())
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
    tid=int(c.data.split(':')[1]); t=await db.tariff_by_id(tid); methods=await db.pay_methods(t['bot_id'])
    if not methods: return await c.message.answer('❌ To‘lov tizimi hali qo‘shilmagan.')
    await c.message.answer(f"💎 Tarif: {t['name']}\n📅 Muddat: {t['days']} kun\n💰 Narx: {fmt_money(t['price'])} so‘m\n\nTo‘lov turini tanlang:", reply_markup=pay_methods_inline(methods,tid)); await c.answer()
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

# STATS LOG BROADCAST REMINDERS
@child_router.message(F.text=='📊 Statistika')
async def child_stats(m:Message):
    if not await is_child_admin(m): return
    bid=await runtime_db_id(m.bot.id); movies=len(await db.list_movies(bid)); prem=len(await db.premium_list(bid)); pays=len(await db.payments(bid)); req=len(await db.requests(bid))
    await m.answer(f"📊 Statistika\n\n🎬 Kinolar: {movies}\n💎 Premiumlar: {prem}\n💳 To‘lovlar: {pays}\n📥 So‘rovlar: {req}")
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
@child_router.message(F.text.in_({'👥 Foydalanuvchilar','⚡ Avtomatik to‘lov tizimlari','📝 Oddiy to‘lov tizimlari','👥 Oddiy (🔒 Ruxsat berish)','🌟 Premium (🔒 Ruxsat berish)'}))
async def child_stubs(m:Message): await m.answer('✅ Bo‘lim tayyor. Kerakli sozlamalarni yuqoridagi tugmalardan boshqaring.')

async def send_part_message(m:Message, mv, p):
    bid=await runtime_db_id(m.bot.id)
    cap=p['caption'] or mv['caption'] or await db.get_setting(bid,'text_Kino_caption_matni','')
    ad_movie=await db.get_setting(bid,'ad_movie','0')
    if ad_movie=='1':
        ads=await db.ads(bid)
        if ads: cap+=(('\n\n' if cap else '')+'📢 '+ads[0]['text'])
    if p['file_id']:
        await m.answer_video(p['file_id'], caption=cap, protect_content=True, reply_markup=movie_inline(mv['id']))

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
    ok,wait=await spam_allowed(bid,m.from_user.id)
    if not ok: return await m.answer(f'⛔ Juda tez-tez yuboryapsiz! Iltimos {wait} soniya kuting...')
    channels=await db.channels(bid)
    if channels and not SUBSCRIPTION_FAKE_VERIFY:
        not_join=[]
        for ch in channels:
            if not ch['checkable']: continue
            try:
                member=await m.bot.get_chat_member(ch['chat_id'], m.from_user.id)
                if member.status in {'left','kicked'}: not_join.append(ch)
            except Exception: not_join.append(ch)
        if not_join:
            return await m.answer('🔐 Kino olish uchun quyidagi kanallarga obuna bo‘ling:\n'+'\n'.join([f"• {x['url']}" for x in not_join]), reply_markup=sub_check())
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
    if bot_id in child_tasks and not child_tasks[bot_id].done(): return
    r=await db.bot_by_id(bot_id)
    if not r or r['status']!='active': return
    async def runner():
        bot=Bot(r['token']); dp=Dispatcher(storage=MemoryStorage()); dp.include_router(child_router)
        log.info('Child bot started @%s', r['username'])
        bg=asyncio.create_task(background_worker(bot,bot_id))
        try: await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except asyncio.CancelledError: pass
        finally:
            bg.cancel(); await bot.session.close()
    child_tasks[bot_id]=asyncio.create_task(runner())
async def stop_child(bot_id:int):
    t=child_tasks.get(bot_id)
    if t and not t.done(): t.cancel()
async def start_all_children():
    for r in await db.bots():
        if r['status']=='active': await start_child(r['id'])
async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN env kerak')
    await db.init_db(); await start_all_children()
    bot=Bot(BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage()); dp.include_router(main_router)
    log.info('%s started', BOT_NAME)
    try: await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally: await bot.session.close()
if __name__=='__main__': asyncio.run(main())
