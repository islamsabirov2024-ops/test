import asyncio

async def safe_broadcast(bot, users, text: str, delay: float = 0.06):
    sent = failed = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(delay)
    return {'sent': sent, 'failed': failed}
