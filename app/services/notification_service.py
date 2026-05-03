from app.services.formatters import fmt_money, fmt_dt

async def send_payment_approved(bot, user_id: int, tariff_name: str, days: int, method: str, amount: int, until_ts: int):
    await bot.send_message(user_id, f"✅ To‘lov tasdiqlandi! #tasdiqlandi\n\n📦 Tarif: {tariff_name}\n📅 Muddat: {days} kun\n💳 To‘lov tizimi: {method}\n💰 Summa: {fmt_money(amount)} so‘m\n⏰ Tugash: {fmt_dt(until_ts)}")
