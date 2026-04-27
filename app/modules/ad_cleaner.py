import asyncio
import re
from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from app.keyboards.common import ad_cleaner_menu

BAD_WORDS = [
    'reklama', 'реклама', 'promo', 'aksiya', 'акция', 'chegirma', 'скидка',
    'obuna bo', 'подпис', 'kanalim', 'kanalga', 'канал', 'pul ishlash', 'tez pul',
    'stavka', 'ставка', 'казино', 'kazino', 'casino', 'bet', '1xbet', 'pin up',
    'aviator', 'bonus', 'накрутка', 'nakrutka', 'auditoriya', 'sotiladi', 'arzon narx'
]

LINK_RE = re.compile(r'(https?://|www\.|t\.me/|telegram\.me/|joinchat/|@\w{4,})', re.I)

WELCOME_TEXT = (
    '🧹 <b>Reklama tozalovchi bot tayyor!</b>\n\n'
    '<blockquote>Botni guruhga qo‘shing, admin qiling va “Delete messages” huquqini bering. '
    'Shundan keyin link, @username, forward va spam so‘zlarni avtomatik o‘chiradi.</blockquote>\n\n'
    '✅ Ssilkalarni o‘chiradi\n'
    '✅ @kanal reklamani o‘chiradi\n'
    '✅ Forward xabarlarni o‘chiradi\n'
    '✅ Spam so‘zlarni o‘chiradi\n'
    '✅ Adminlar xabariga tegmaydi'
)

HELP_TEXT = (
    '📌 <b>Qanday ishlaydi?</b>\n\n'
    '<blockquote>Guruhga kelgan har bir xabar tekshiriladi. Reklama belgisi topilsa, bot xabarni '
    'o‘chiradi va qisqa ogohlantirish chiqaradi.</blockquote>\n\n'
    '🧹 <b>O‘chiriladiganlar:</b>\n'
    '• http / https / www linklar\n'
    '• t.me / telegram.me linklar\n'
    '• @username ko‘rinishidagi kanal reklamalari\n'
    '• forward qilingan xabarlar\n'
    '• casino, bet, reklama, aksiya kabi spam so‘zlar\n\n'
    '⚠️ <b>Shart:</b> bot guruhda admin bo‘lishi va <code>Delete messages</code> huquqi bo‘lishi kerak.'
)


def has_forward(message: Message) -> bool:
    return bool(
        getattr(message, 'forward_origin', None)
        or getattr(message, 'forward_from_chat', None)
        or getattr(message, 'forward_from', None)
        or getattr(message, 'forward_sender_name', None)
    )


def has_link_entities(message: Message) -> bool:
    entities = list(message.entities or []) + list(message.caption_entities or [])
    return any(e.type in {'url', 'text_link', 'mention'} for e in entities)


def has_url_buttons(message: Message) -> bool:
    markup = getattr(message, 'reply_markup', None)
    if not markup or not getattr(markup, 'inline_keyboard', None):
        return False
    for row in markup.inline_keyboard:
        for btn in row:
            if getattr(btn, 'url', None):
                return True
    return False


def is_ad_message(message: Message) -> tuple[bool, str]:
    text = (message.text or message.caption or '').lower()
    if has_forward(message):
        return True, 'forward'
    if has_url_buttons(message):
        return True, 'url button'
    if has_link_entities(message) or LINK_RE.search(text):
        return True, 'ssilka / @username'
    for word in BAD_WORDS:
        if word in text:
            return True, 'spam so‘z'
    return False, ''


async def is_admin_message(message: Message) -> bool:
    if not message.from_user:
        return False
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in {'creator', 'administrator'}
    except Exception:
        return False


async def bot_can_delete(message: Message) -> bool:
    try:
        me = await message.bot.get_me()
        member = await message.bot.get_chat_member(message.chat.id, me.id)
        return bool(member.status == 'administrator' and getattr(member, 'can_delete_messages', False))
    except Exception:
        return False


async def safe_delete(message: Message) -> bool:
    try:
        await message.delete()
        return True
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    except Exception:
        return False


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    @r.message(CommandStart())
    async def start(m: Message):
        await m.answer(WELCOME_TEXT, reply_markup=ad_cleaner_menu())

    @r.message(Command('help'))
    async def help_cmd(m: Message):
        await m.answer(HELP_TEXT, reply_markup=ad_cleaner_menu())

    @r.message(Command('status'))
    async def status_cmd(m: Message):
        if m.chat.type in {'group', 'supergroup'}:
            can_delete = await bot_can_delete(m)
            status = '✅ Delete messages huquqi bor' if can_delete else '❌ Delete messages huquqi yo‘q'
            await m.answer(f'🧹 <b>Status</b>\n\n<blockquote>{status}</blockquote>', reply_markup=ad_cleaner_menu())
        else:
            await m.answer('✅ <b>Bot ishlayapti.</b>\n<blockquote>Tekshirish uchun meni guruhga admin qilib qo‘shing.</blockquote>', reply_markup=ad_cleaner_menu())

    @r.callback_query(F.data.startswith('ad:'))
    async def ad_cb(c: CallbackQuery):
        if c.data == 'ad:status':
            await c.message.answer('✅ <b>Reklama tozalash yoqilgan.</b>\n\n<blockquote>Guruhda admin bo‘lsa, real vaqtda link, forward va spam xabarlarni o‘chiradi.</blockquote>', reply_markup=ad_cleaner_menu())
        elif c.data == 'ad:help':
            await c.message.answer(HELP_TEXT, reply_markup=ad_cleaner_menu())
        else:
            await c.message.answer(WELCOME_TEXT, reply_markup=ad_cleaner_menu())
        await c.answer()

    @r.message(F.chat.type.in_({'group', 'supergroup'}))
    async def clean(m: Message):
        if not m.from_user:
            return
        if await is_admin_message(m):
            return
        is_ad, reason = is_ad_message(m)
        if not is_ad:
            return
        deleted = await safe_delete(m)
        if not deleted:
            return
        try:
            warn = await m.answer(
                f'🧹 <b>Reklama o‘chirildi</b>\n'
                f'<blockquote>Sabab: {reason}\nUser: {m.from_user.full_name}</blockquote>'
            )
            await asyncio.sleep(7)
            await safe_delete(warn)
        except Exception:
            pass

    dp.include_router(r)
