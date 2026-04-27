from __future__ import annotations

import asyncio
import re
from datetime import datetime
from aiogram import Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db import get_settings, save_settings
from app.keyboards.common import ad_cleaner_menu, ad_cleaner_reply, ad_settings_menu

DEFAULT_SETTINGS = {
    'clean_links': True,
    'clean_mentions': True,
    'clean_forwards': True,
    'clean_spam': True,
    'clean_buttons': True,
    'ignore_admins': True,
    'warn_enabled': True,
    'deleted_count': 0,
    'link_count': 0,
    'mention_count': 0,
    'forward_count': 0,
    'spam_count': 0,
    'button_count': 0,
    'last_reason': '',
    'last_user': '',
    'last_time': '',
    'blacklist': [
        'reklama', 'реклама', 'promo', 'aksiya', 'акция', 'chegirma', 'скидка',
        'obuna bo', 'подпис', 'kanalim', 'kanalga', 'канал', 'pul ishlash', 'tez pul',
        'stavka', 'ставка', 'казино', 'kazino', 'casino', 'bet', '1xbet', 'pin up',
        'aviator', 'bonus', 'накрутка', 'nakrutka', 'auditoriya', 'sotiladi', 'arzon narx',
    ],
}

LINK_RE = re.compile(r'(https?://|www\.|t\.me/|telegram\.me/|joinchat/|bit\.ly/|tinyurl\.com/|instagram\.com/|tiktok\.com/)', re.I)
MENTION_RE = re.compile(r'(^|\s)@[A-Za-z0-9_]{4,}', re.I)

WELCOME_TEXT = (
    '🧹 <b>Reklama tozalovchi bot tayyor!</b>\n\n'
    '<blockquote>Botni guruhga qo‘shing, admin qiling va “Delete messages” huquqini bering. '
    'Shundan keyin ssilka, @username, forward, URL tugma va spam so‘zlarni avtomatik o‘chiradi.</blockquote>\n\n'
    '✅ Ssilkalarni o‘chiradi\n'
    '✅ @kanal reklamani o‘chiradi\n'
    '✅ Forward xabarlarni o‘chiradi\n'
    '✅ URL tugmali reklamani o‘chiradi\n'
    '✅ Spam so‘zlarni o‘chiradi\n'
    '✅ Adminlar xabariga tegmaydi'
)

HELP_TEXT = (
    '📚 <b>Qo‘llanma</b>\n\n'
    '<blockquote>1) Botni guruhga qo‘shing.\n'
    '2) Botni admin qiling.\n'
    '3) Delete messages huquqini yoqing.\n'
    '4) BotFather → /setprivacy → Disable qiling.\n'
    '5) Guruhga reklama link tashlab test qiling.</blockquote>\n\n'
    '🧹 <b>O‘chiriladiganlar:</b>\n'
    '• http / https / www linklar\n'
    '• t.me / telegram.me / invite linklar\n'
    '• @username ko‘rinishidagi kanal reklamalari\n'
    '• forward qilingan xabarlar\n'
    '• inline URL tugmali postlar\n'
    '• casino, bet, reklama, aksiya kabi spam so‘zlar\n\n'
    '⚠️ <b>Shart:</b> bot guruhda admin bo‘lishi va <code>Delete messages</code> huquqi bo‘lishi kerak.'
)


def merge_settings(data: dict | None) -> dict:
    merged = dict(DEFAULT_SETTINGS)
    if data:
        for k, v in data.items():
            merged[k] = v
    if not isinstance(merged.get('blacklist'), list):
        merged['blacklist'] = list(DEFAULT_SETTINGS['blacklist'])
    return merged


async def load_settings(bot_id: int) -> dict:
    data = merge_settings(await get_settings(bot_id))
    await save_settings(bot_id, data)
    return data


async def store_settings(bot_id: int, data: dict) -> None:
    await save_settings(bot_id, merge_settings(data))


def has_forward(message: Message) -> bool:
    return bool(
        getattr(message, 'forward_origin', None)
        or getattr(message, 'forward_from_chat', None)
        or getattr(message, 'forward_from', None)
        or getattr(message, 'forward_sender_name', None)
    )


def has_url_entities(message: Message) -> bool:
    entities = list(message.entities or []) + list(message.caption_entities or [])
    return any(e.type in {'url', 'text_link'} for e in entities)


def has_mention_entities(message: Message) -> bool:
    entities = list(message.entities or []) + list(message.caption_entities or [])
    return any(e.type == 'mention' for e in entities)


def has_url_buttons(message: Message) -> bool:
    markup = getattr(message, 'reply_markup', None)
    if not markup or not getattr(markup, 'inline_keyboard', None):
        return False
    for row in markup.inline_keyboard:
        for btn in row:
            if getattr(btn, 'url', None):
                return True
    return False


def detect_ad(message: Message, settings: dict) -> tuple[bool, str, str]:
    text = (message.text or message.caption or '').lower()

    if settings.get('clean_forwards', True) and has_forward(message):
        return True, 'forward', 'forward_count'

    if settings.get('clean_buttons', True) and has_url_buttons(message):
        return True, 'URL tugma', 'button_count'

    if settings.get('clean_links', True) and (has_url_entities(message) or LINK_RE.search(text)):
        return True, 'ssilka', 'link_count'

    if settings.get('clean_mentions', True) and (has_mention_entities(message) or MENTION_RE.search(text)):
        return True, '@kanal', 'mention_count'

    if settings.get('clean_spam', True):
        for word in settings.get('blacklist', DEFAULT_SETTINGS['blacklist']):
            if str(word).lower() in text:
                return True, f'spam so‘z: {word}', 'spam_count'

    return False, '', ''


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


def status_text(settings: dict, can_delete: bool | None = None) -> str:
    delete_line = ''
    if can_delete is not None:
        delete_line = '✅ Delete messages huquqi bor' if can_delete else '❌ Delete messages huquqi yo‘q'
        delete_line += '\n'
    return (
        '✅ <b>Qorovul bot status</b>\n\n'
        f'<blockquote>{delete_line}'
        f'🔗 Ssilka: {"✅" if settings.get("clean_links", True) else "❌"}\n'
        f'@️⃣ @kanal: {"✅" if settings.get("clean_mentions", True) else "❌"}\n'
        f'📨 Forward: {"✅" if settings.get("clean_forwards", True) else "❌"}\n'
        f'🔘 URL tugma: {"✅" if settings.get("clean_buttons", True) else "❌"}\n'
        f'🚫 Spam so‘z: {"✅" if settings.get("clean_spam", True) else "❌"}\n'
        f'👮 Adminlar: {"tegmaydi" if settings.get("ignore_admins", True) else "tekshiradi"}\n\n'
        f'🧹 O‘chirilgan jami: {int(settings.get("deleted_count", 0) or 0)} ta</blockquote>'
    )


def log_text(settings: dict) -> str:
    return (
        '🧾 <b>Tozalash logi</b>\n\n'
        f'<blockquote>Jami: {int(settings.get("deleted_count", 0) or 0)}\n'
        f'🔗 Ssilka: {int(settings.get("link_count", 0) or 0)}\n'
        f'@️⃣ @kanal: {int(settings.get("mention_count", 0) or 0)}\n'
        f'📨 Forward: {int(settings.get("forward_count", 0) or 0)}\n'
        f'🔘 URL tugma: {int(settings.get("button_count", 0) or 0)}\n'
        f'🚫 Spam: {int(settings.get("spam_count", 0) or 0)}\n\n'
        f'Oxirgi sabab: {settings.get("last_reason") or "-"}\n'
        f'Oxirgi user: {settings.get("last_user") or "-"}\n'
        f'Oxirgi vaqt: {settings.get("last_time") or "-"}</blockquote>'
    )


def blacklist_text(settings: dict) -> str:
    words = settings.get('blacklist', []) or []
    shown = ', '.join(str(w) for w in words[:60])
    return (
        '🚫 <b>Blacklist so‘zlar</b>\n\n'
        f'<blockquote>{shown}</blockquote>\n\n'
        'Hozircha so‘zlar tayyor ro‘yxat orqali ishlaydi. Keyingi versiyada tugma orqali qo‘shish/o‘chirish ham ulanadi.'
    )


def setup(dp: Dispatcher, bot_id: int, owner_id: int):
    r = Router()

    async def owner_only(c: CallbackQuery) -> bool:
        if c.from_user.id != owner_id:
            await c.answer('Bu sozlama faqat bot egasiga tegishli.', show_alert=True)
            return False
        return True

    async def show_home(message: Message) -> None:
        await load_settings(bot_id)
        await message.answer(WELCOME_TEXT, reply_markup=ad_cleaner_menu())
        if message.chat.type == 'private':
            await message.answer('🧹 <b>Qorovul bot menyusi</b>', reply_markup=ad_cleaner_reply())

    @r.message(CommandStart())
    async def start(m: Message):
        await show_home(m)

    @r.message(Command('help'))
    async def help_cmd(m: Message):
        await m.answer(HELP_TEXT, reply_markup=ad_cleaner_menu())

    @r.message(Command('status'))
    async def status_cmd(m: Message):
        s = await load_settings(bot_id)
        can_delete = await bot_can_delete(m) if m.chat.type in {'group', 'supergroup'} else None
        await m.answer(status_text(s, can_delete), reply_markup=ad_cleaner_menu())

    @r.message(F.chat.type == 'private', F.text.in_({'✅ Status', '⚙️ Sozlamalar', '🚫 Blacklist', '🧾 Tozalash logi', '🧪 Test', '🧹 Keshni tozalash', '📚 Qo‘llanma', '◀️ Orqaga'}))
    async def private_menu(m: Message):
        if m.from_user.id != owner_id:
            await m.answer('Bu bot guruhda reklama tozalash uchun ishlaydi. Guruhga qo‘shib admin qiling.')
            return
        s = await load_settings(bot_id)
        text = (m.text or '').strip()
        if text == '✅ Status':
            await m.answer(status_text(s), reply_markup=ad_cleaner_menu())
        elif text == '⚙️ Sozlamalar':
            await m.answer('⚙️ <b>Qorovul sozlamalari</b>\n\n<blockquote>Kerakli filtrni yoqing yoki o‘chiring.</blockquote>', reply_markup=ad_settings_menu(s))
        elif text == '🚫 Blacklist':
            await m.answer(blacklist_text(s), reply_markup=ad_cleaner_menu())
        elif text == '🧾 Tozalash logi':
            await m.answer(log_text(s), reply_markup=ad_cleaner_menu())
        elif text == '🧪 Test':
            await m.answer('🧪 <b>Test matn:</b> <code>https://t.me/test @kanal reklama</code>\n\n<blockquote>Shuni guruhga tashlasangiz bot o‘chirishi kerak.</blockquote>', reply_markup=ad_cleaner_menu())
        elif text == '🧹 Keshni tozalash':
            s['last_reason'] = ''
            s['last_user'] = ''
            s['last_time'] = ''
            await store_settings(bot_id, s)
            await m.answer('🧹 <b>Kesh tozalandi.</b>', reply_markup=ad_cleaner_menu())
        elif text == '📚 Qo‘llanma':
            await m.answer(HELP_TEXT, reply_markup=ad_cleaner_menu())
        else:
            await show_home(m)

    @r.callback_query(F.data.startswith('ad:'))
    async def ad_cb(c: CallbackQuery):
        s = await load_settings(bot_id)
        data = c.data or ''

        if data in {'ad:settings', 'ad:toggle:clean_links', 'ad:toggle:clean_mentions', 'ad:toggle:clean_forwards', 'ad:toggle:clean_spam', 'ad:toggle:clean_buttons', 'ad:toggle:ignore_admins', 'ad:toggle:warn_enabled', 'ad:cache'}:
            if not await owner_only(c):
                return

        if data == 'ad:status':
            can_delete = await bot_can_delete(c.message) if c.message.chat.type in {'group', 'supergroup'} else None
            await c.message.answer(status_text(s, can_delete), reply_markup=ad_cleaner_menu())
        elif data == 'ad:help':
            await c.message.answer(HELP_TEXT, reply_markup=ad_cleaner_menu())
        elif data == 'ad:settings':
            await c.message.answer('⚙️ <b>Qorovul sozlamalari</b>\n\n<blockquote>Har bir filtrni alohida yoqib/o‘chirishingiz mumkin.</blockquote>', reply_markup=ad_settings_menu(s))
        elif data.startswith('ad:toggle:'):
            key = data.split(':', 2)[2]
            s[key] = not bool(s.get(key, True))
            await store_settings(bot_id, s)
            await c.message.answer('✅ <b>Sozlama yangilandi.</b>', reply_markup=ad_settings_menu(s))
        elif data == 'ad:blacklist':
            await c.message.answer(blacklist_text(s), reply_markup=ad_cleaner_menu())
        elif data == 'ad:log':
            await c.message.answer(log_text(s), reply_markup=ad_cleaner_menu())
        elif data == 'ad:test':
            await c.message.answer('🧪 <b>Test uchun:</b> guruhga <code>https://t.me/test @kanal reklama</code> yuboring. Bot admin bo‘lsa o‘chiradi.', reply_markup=ad_cleaner_menu())
        elif data == 'ad:cache':
            s['last_reason'] = ''
            s['last_user'] = ''
            s['last_time'] = ''
            await store_settings(bot_id, s)
            await c.message.answer('🧹 <b>Kesh tozalandi.</b>', reply_markup=ad_cleaner_menu())
        else:
            await c.message.answer(WELCOME_TEXT, reply_markup=ad_cleaner_menu())
        await c.answer()

    @r.message(F.chat.type.in_({'group', 'supergroup'}))
    async def clean(m: Message):
        if not m.from_user:
            return
        s = await load_settings(bot_id)
        if s.get('ignore_admins', True) and await is_admin_message(m):
            return

        is_ad, reason, counter_key = detect_ad(m, s)
        if not is_ad:
            return

        deleted = await safe_delete(m)
        if not deleted:
            return

        s['deleted_count'] = int(s.get('deleted_count', 0) or 0) + 1
        if counter_key:
            s[counter_key] = int(s.get(counter_key, 0) or 0) + 1
        s['last_reason'] = reason
        s['last_user'] = f'{m.from_user.full_name} ({m.from_user.id})'
        s['last_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        await store_settings(bot_id, s)

        if not s.get('warn_enabled', True):
            return
        try:
            warn = await m.answer(
                '🧹 <b>Reklama o‘chirildi</b>\n'
                f'<blockquote>Sabab: {reason}\nUser: {m.from_user.full_name}</blockquote>'
            )
            await asyncio.sleep(6)
            await safe_delete(warn)
        except Exception:
            pass

    dp.include_router(r)
