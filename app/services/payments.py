import time
from app import database as db
from app.constants import BOT_STATUS_ACTIVE

async def approve_payment(payment_id:int):
    payments = await db.list_payments('pending')
    p = next((x for x in payments if x['id'] == payment_id), None)
    if not p:
        return False
    await db.decide_payment(payment_id, 'approved')
    paid_until = int(time.time()) + 30*24*3600
    await db.update_bot_fields(p['bot_id'], paid_until=paid_until, status=BOT_STATUS_ACTIVE)
    return True

async def reject_payment(payment_id:int):
    await db.decide_payment(payment_id, 'rejected')
    return True
