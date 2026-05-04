from app import db

async def ensure_user(user_id: int, ref_by: int | None = None):
    await db.add_user(user_id, ref_by)
    return await db.get_user(user_id)

async def profile(user_id: int):
    return await db.get_user(user_id)

async def add_real_balance(user_id: int, amount: int):
    return await db.add_balance(user_id, amount)
