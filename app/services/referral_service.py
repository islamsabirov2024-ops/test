from app import db

async def give_referral_bonus(bot_id: int, inviter_id: int) -> int:
    bonus = int(await db.get_setting(bot_id, 'referral_bonus', '0') or 0)
    if bonus > 0:
        await db.add_referral_balance(bot_id, inviter_id, bonus)
    return bonus

async def can_buy_with_referral(bot_id: int, user_id: int, price: int) -> bool:
    return int(await db.referral_balance(bot_id, user_id)) >= int(price)

async def pay_tariff_with_referral(bot_id: int, user_id: int, price: int) -> bool:
    # Referral balance is separate; no mixed payment with real money.
    return await db.take_referral_balance(bot_id, user_id, int(price))
