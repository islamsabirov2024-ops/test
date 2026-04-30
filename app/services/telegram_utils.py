from telegram import Bot

async def validate_token(token: str):
    bot = Bot(token=token.strip())
    me = await bot.get_me()
    return me.username or '', me.first_name or ''
