from app import db

async def add(bot_id: int, name: str, days: int, price: int):
    price = max(1000, min(1000000, int(price)))
    days = max(1, int(days))
    return await db.add_tariff(bot_id, name, days, price)

async def edit(tariff_id: int, bot_id: int, field: str, value: str):
    return await db.update_tariff(tariff_id, bot_id, field, value)
