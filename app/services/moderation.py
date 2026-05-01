import time
from telegram import ChatPermissions
from app.utils.telegram import has_link_or_ad
from app import database as db

async def process_group_message(update, context, bot_id:int):
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or user.is_bot:
        return
    if msg.new_chat_members:
        for m in msg.new_chat_members:
            inviter = user.id
            await db.inc_invite(bot_id, msg.chat_id, inviter, 1)
        return
    text = msg.text or msg.caption or ''
    if not has_link_or_ad(text):
        return
    bot_row = context.application.bot_data.get('bot_row')
    required = int(bot_row.get('required_invites') or 5)
    count = await db.get_invite_count(bot_id, msg.chat_id, user.id)
    if count >= required:
        return
    try:
        await msg.delete()
    except Exception:
        pass
    mute_seconds = int(bot_row.get('mute_seconds') or 30)
    try:
        until = int(time.time()) + mute_seconds
        await context.bot.restrict_chat_member(msg.chat_id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=until)
        await context.bot.send_message(msg.chat_id, f"🚫 {user.mention_html()} reklama yubordi.\n👥 Yozish uchun {required} odam qo‘shish kerak.\n⏱ {mute_seconds} sekund bloklandi.", parse_mode='HTML')
    except Exception:
        pass
