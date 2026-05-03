import time
from app import db

async def run_once(bot):
    now = int(time.time())
    rows = await db.due_ads(now)
    for ad in rows:
        # Actual user target selection is handled in main router.
        await db.mark_ad_sent(ad['id'])
