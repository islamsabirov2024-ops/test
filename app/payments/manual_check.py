def payment_caption(tariff_name: str, days: int, user_id: int, amount: int, method: str) -> str:
    return f"🧾 Yangi to‘lov\n\n📦 Tarif: {tariff_name}\n📅 Muddat: {days} kun\n👤 User: {user_id}\n💰 Summa: {amount:,} so‘m\n💳 Usul: {method}".replace(',', ' ')
