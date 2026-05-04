import time
from app import db

async def run_once(bot):
    now = int(time.time())
    rows = await db.premium_expiring(now + 86400)
    for row in rows:
        try:
            await bot.send_message(row['user_id'], '⏰ Premium muddati 1 kundan keyin tugaydi.')
            await db.mark_premium_reminded(row['bot_id'], row['user_id'])
        except Exception:
            pass
