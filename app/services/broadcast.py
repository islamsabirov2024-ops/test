from app import database as db

async def broadcast_text(bot, bot_id:int, text:str):
    async with await db.connect() as conn:
        cur = await conn.execute("SELECT user_id FROM subscribers WHERE bot_id=?", (bot_id,))
        users = [r['user_id'] for r in await cur.fetchall()]
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass
    return sent, len(users)
