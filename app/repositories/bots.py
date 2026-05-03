from app import db

async def create_bot(owner_id: int, token: str, username: str, title: str):
    return await db.add_bot(owner_id, token, username, title)

async def list_owner_bots(owner_id: int):
    return await db.bots(owner_id)

async def set_status(bot_id: int, status: str):
    return await db.set_bot_status(bot_id, status)
