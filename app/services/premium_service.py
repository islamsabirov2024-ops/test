from app import db

async def grant_from_tariff(bot_id: int, user_id: int, tariff) -> int:
    days = int(tariff['days']) if tariff else 0
    return await db.grant_premium(bot_id, user_id, days)

async def is_active(bot_id: int, user_id: int) -> bool:
    return await db.has_premium(bot_id, user_id)
