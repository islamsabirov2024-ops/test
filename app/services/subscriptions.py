from telegram.error import TelegramError
from app import database as db

async def check_required_subscriptions(bot, bot_id:int, user_id:int) -> bool:
    enabled = await db.get_setting(bot_id, 'force_sub_enabled', '0')
    fake = await db.get_setting(bot_id, 'sub_fake_verify', '0')
    if enabled != '1' or fake == '1':
        return True
    channels = await db.list_channels(bot_id)
    checkable = [c for c in channels if int(c.get('is_checkable') or 0) == 1 and c.get('chat_id')]
    if not checkable:
        return True
    for ch in checkable:
        try:
            member = await bot.get_chat_member(ch['chat_id'], user_id)
            if member.status in ('left', 'kicked'):
                return False
        except TelegramError:
            return False
    return True
