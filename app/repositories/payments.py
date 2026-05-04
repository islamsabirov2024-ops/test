from app import db

async def create_payment(bot_id: int, user_id: int, amount: int, method: str, screenshot_file_id: str, tariff_id: int = 0):
    return await db.add_payment(bot_id, user_id, amount, method, 'pending', screenshot_file_id, tariff_id)

async def approve(payment_id: int):
    return await db.update_payment(payment_id, 'approved')

async def reject(payment_id: int):
    return await db.update_payment(payment_id, 'rejected')
