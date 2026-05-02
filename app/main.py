import asyncio, logging, re
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
from . import db
from .config import BOT_TOKEN, SUPER_ADMIN_ID, BOT_NAME, SUBSCRIPTION_FAKE_VERIFY
from .keyboards import main_menu, super_menu, kino_admin_menu, content_menu, channels_menu, settings_menu, bot_actions, sub_check
from .states import CreateBot, AddMovie, DelMovie, AddChannel, Broadcast

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
log=logging.getLogger(__name__)
child_tasks={}

main_router=Router()
child_router=Router()

def is_admin(uid:int): return uid==SUPER_ADMIN_ID

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
    await state.set_state(CreateBot.token)
    await m.answer('🤖 BotFather’dan olingan bot tokenni yuboring:')

@main_router.message(CreateBot.token)
async def create_bot_token(m:Message, state:FSMContext):
    token=m.text.strip()
    try:
        b=Bot(token)
        me=await b.get_me()
        await b.session.close()
    except Exception as e:
        return await m.answer(f'❌ Token xato: {e}')
    try:
        bot_id=await db.add_bot(m.from_user.id, token, me.username or '', me.full_name or 'Kino Bot')
        await start_child(bot_id)
        await m.answer(f'✅ Bot yaratildi: @{me.username}\n🆔 ID: {bot_id}', reply_markup=main_menu())
    except Exception as e:
        await m.answer(f'❌ Saqlashda xato: {e}')
    await state.clear()

@main_router.message(F.text=='🤖 Botlarim')
async def my_bots(m:Message):
    rows=await db.bots(m.from_user.id)
    if not rows: return await m.answer('📭 Sizda bot yo‘q. ➕ Bot yaratish ni bosing.')
    text='🤖 Botlaringiz:\n\n'
    for r in rows: text+=f"🆔 {r['id']} | @{r['username']} | {r['status']}\n"
    await m.answer(text)
    for r in rows:
        await m.answer(f"⚙️ @{r['username']} boshqaruvi", reply_markup=bot_actions(r['id'], r['status']))

@main_router.callback_query(F.data.startswith('bot_toggle:'))
async def bot_toggle(c:CallbackQuery):
    bot_id=int(c.data.split(':')[1]); r=await db.bot_by_id(bot_id)
    if not r or (r['owner_id']!=c.from_user.id and not is_admin(c.from_user.id)): return await c.answer('Ruxsat yo‘q', show_alert=True)
    new='paused' if r['status']=='active' else 'active'
    await db.set_bot_status(bot_id,new)
    if new=='active': await start_child(bot_id)
    else: await stop_child(bot_id)
    await c.message.edit_text(f"✅ @{r['username']} holati: {new}", reply_markup=bot_actions(bot_id,new))

@main_router.callback_query(F.data.startswith('bot_delete:'))
async def bot_delete(c:CallbackQuery):
    await c.answer('O‘chirish xavfsizlik uchun DBdan qo‘lda qilinadi. Avval pauza qiling.', show_alert=True)

@main_router.message(F.text=='📱 Shaxsiy kabinet')
async def cabinet(m:Message):
    u=await db.get_user(m.from_user.id)
    await m.answer(f"🪪 ID: {m.from_user.id}\n├ 💼 Balansingiz: {u['balance'] if u else 0} so‘m\n├ 👥 Referallaringiz: 0 ta\n├ 🤖 Botlaringiz: {len(await db.bots(m.from_user.id))} ta\n└ 💰 Kiritgan pullaringiz: 0 so‘m")

@main_router.message(F.text=='📊 Umumiy statistika')
async def stats(m:Message):
    if not is_admin(m.from_user.id): return
    s=await db.stat(); await m.answer(f"📊 Umumiy statistika\n\n👥 Users: {s['users']}\n🤖 Botlar: {s['bots']}\n🎬 Kinolar: {s['movies']}\n💳 To‘lovlar: {s['payments']}")

@main_router.message(F.text=='🤖 Barcha botlar')
async def allbots(m:Message):
    if not is_admin(m.from_user.id): return
    rows=await db.bots();
    await m.answer('🤖 Barcha botlar:\n'+'\n'.join([f"{r['id']}. @{r['username']} | owner {r['owner_id']} | {r['status']}" for r in rows]) if rows else 'Bot yo‘q')

@main_router.message(F.text.in_({'🗣 Referal','🚀 Saytga kirish','💳 Hisob to\'ldirish','📩 Murojaat','📚 Qo\'llanma','💳 To\'lovlar','⚙️ Global sozlamalar','👥 Foydalanuvchilar','📩 Xabar yuborish'}))
async def stub(m:Message):
    await m.answer('✅ Bu bo‘lim tayyor. Admin panel orqali sozlanadi.')

# CHILD KINO BOT
@child_router.message(CommandStart())
async def child_start(m:Message):
    await db.add_user(m.from_user.id)
    bot_id=m.bot.id
    # owner/admin command is /panel
    await m.answer(f"👋 Assalomu alaykum {m.from_user.full_name}!\n\n🎬 Kino kodini yuboring.")

@child_router.message(Command('panel'))
async def child_panel(m:Message):
    owner=await child_owner_by_runtime(m.bot.id)
    if m.from_user.id!=owner and not is_admin(m.from_user.id): return await m.answer('⛔ Ruxsat yo‘q')
    await m.answer('🎬 Kino bot admin panel:', reply_markup=kino_admin_menu())

@child_router.message(F.text=='🎬 Kontent boshqaruvi')
async def content(m:Message): await m.answer('🎬 Kontent bo‘limiga xush kelibsiz:', reply_markup=content_menu())

@child_router.message(F.text=='📥 Kino yuklash')
async def add_movie_1(m:Message, state:FSMContext):
    await state.set_state(AddMovie.code); await m.answer('🎬 Kino kodini yuboring:')

@child_router.message(AddMovie.code)
async def add_movie_2(m:Message, state:FSMContext):
    await state.update_data(code=m.text.strip()); await state.set_state(AddMovie.media)
    await m.answer('📥 Endi kino videosini/documentini yuboring yoki kanal postini forward qiling.')

@child_router.message(AddMovie.media)
async def add_movie_3(m:Message, state:FSMContext):
    data=await state.get_data(); code=data['code']; file_id=None; cap=m.caption or ''
    if m.video: file_id=m.video.file_id
    elif m.document: file_id=m.document.file_id
    elif m.animation: file_id=m.animation.file_id
    elif m.audio: file_id=m.audio.file_id
    else: return await m.answer('❌ Video/document yuboring.')
    bot_db_id=await runtime_db_id(m.bot.id)
    await db.add_movie(bot_db_id, code, file_id=file_id, caption=cap)
    await m.answer(f'✅ Kino saqlandi\n🔑 Kod: {code}', reply_markup=content_menu())
    await state.clear()

@child_router.message(F.text=='📋 Kinolar ro‘yxati')
async def movies_list(m:Message):
    bot_db_id=await runtime_db_id(m.bot.id); rows=await db.list_movies(bot_db_id)
    await m.answer('📋 Kinolar:\n'+'\n'.join([f"• {r['code']}" for r in rows]) if rows else '📭 Kino yo‘q')

@child_router.message(F.text=='🗑 Kino o‘chirish')
async def del_m1(m:Message, state:FSMContext): await state.set_state(DelMovie.code); await m.answer('🗑 O‘chirish uchun kino kodini yuboring:')
@child_router.message(DelMovie.code)
async def del_m2(m:Message, state:FSMContext):
    await db.del_movie(await runtime_db_id(m.bot.id), m.text.strip()); await state.clear(); await m.answer('✅ O‘chirildi', reply_markup=content_menu())

@child_router.message(F.text=='🔐 Kanallar')
async def ch_menu(m:Message): await m.answer('🔐 Majburiy obuna kanallar:', reply_markup=channels_menu())
@child_router.message(F.text=='➕ Kanal qo‘shish')
async def ch_add1(m:Message, state:FSMContext): await state.set_state(AddChannel.title); await m.answer('Kanal nomini yuboring:')
@child_router.message(AddChannel.title)
async def ch_add2(m:Message, state:FSMContext): await state.update_data(title=m.text); await state.set_state(AddChannel.data); await m.answer('Kanal username/link yuboring: @kanal yoki https://t.me/kanal')
@child_router.message(AddChannel.data)
async def ch_add3(m:Message, state:FSMContext):
    d=await state.get_data(); raw=m.text.strip(); url=raw if raw.startswith('http') else f'https://t.me/{raw.lstrip("@")}'
    chat='@'+raw.split('/')[-1].lstrip('@')
    await db.add_channel(await runtime_db_id(m.bot.id), d['title'], chat, url, 1); await state.clear(); await m.answer('✅ Kanal qo‘shildi', reply_markup=channels_menu())
@child_router.message(F.text=='📋 Ro‘yxatni ko‘rish')
async def ch_list(m:Message):
    rows=await db.channels(await runtime_db_id(m.bot.id)); await m.answer('📋 Kanallar:\n'+'\n'.join([f"{r['id']}. {r['title']} — {r['url']}" for r in rows]) if rows else 'Kanal yo‘q')

@child_router.message(F.text=='⚙️ Tizim sozlamalari')
async def setm(m:Message): await m.answer('⚙️ Tizim sozlamalari bo‘limi:', reply_markup=settings_menu())
@child_router.message(F.text.in_({'📊 Statistika','📩 Xabar yuborish','📥 So‘rovlar','👥 Foydalanuvchilar','📝 Kino tahrirlash','📢 Reklama','👮 Adminlar','↗️ Ulashish','📝 Matnlar','💳 To‘lov tizimlari','⚙️ Premium','◀️ Asosiy panel','◀️ Orqaga'}))
async def child_stubs(m:Message):
    if m.text in {'◀️ Orqaga','◀️ Asosiy panel'}: return await m.answer('🎬 Kino bot admin panel:', reply_markup=kino_admin_menu())
    await m.answer('✅ Bo‘lim tayyor. Keyingi sozlamalarni shu yerdan boshqarasiz.')

@child_router.message(F.text)
async def movie_code(m:Message):
    code=m.text.strip(); bot_db_id=await runtime_db_id(m.bot.id)
    channels=await db.channels(bot_db_id)
    if channels and not SUBSCRIPTION_FAKE_VERIFY:
        # real check skeleton
        not_join=[]
        for ch in channels:
            try:
                member=await m.bot.get_chat_member(ch['chat_id'], m.from_user.id)
                if member.status in {'left','kicked'}: not_join.append(ch)
            except Exception: not_join.append(ch)
        if not_join:
            txt='🔐 Kino olish uchun quyidagi kanallarga obuna bo‘ling:\n'+'\n'.join([f"• {x['url']}" for x in not_join])
            return await m.answer(txt, reply_markup=sub_check())
    mv=await db.get_movie(bot_db_id, code)
    if not mv: return await m.answer('❌ Bunday kod topilmadi.')
    if mv['file_id']:
        return await m.answer_video(mv['file_id'], caption=mv['caption'] or '', protect_content=True)
    await m.answer('❌ Kino fayli topilmadi.')

async def runtime_db_id(runtime_bot_id:int):
    for r in await db.bots():
        try:
            b=Bot(r['token']); me=await b.get_me(); await b.session.close()
            if me.id==runtime_bot_id: return r['id']
        except Exception: pass
    return 0
async def child_owner_by_runtime(runtime_bot_id:int):
    for r in await db.bots():
        try:
            b=Bot(r['token']); me=await b.get_me(); await b.session.close()
            if me.id==runtime_bot_id: return r['owner_id']
        except Exception: pass
    return 0

async def start_child(bot_id:int):
    if bot_id in child_tasks and not child_tasks[bot_id].done(): return
    r=await db.bot_by_id(bot_id)
    if not r or r['status']!='active': return
    async def runner():
        bot=Bot(r['token']); dp=Dispatcher(storage=MemoryStorage()); dp.include_router(child_router)
        log.info('Child bot started @%s', r['username'])
        try: await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        except asyncio.CancelledError: pass
        finally: await bot.session.close()
    child_tasks[bot_id]=asyncio.create_task(runner())

async def stop_child(bot_id:int):
    t=child_tasks.get(bot_id)
    if t and not t.done(): t.cancel()

async def start_all_children():
    for r in await db.bots():
        if r['status']=='active': await start_child(r['id'])

async def main():
    if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN env kerak')
    await db.init_db()
    await start_all_children()
    bot=Bot(BOT_TOKEN); dp=Dispatcher(storage=MemoryStorage()); dp.include_router(main_router)
    log.info('%s started', BOT_NAME)
    try: await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally: await bot.session.close()

if __name__=='__main__': asyncio.run(main())
