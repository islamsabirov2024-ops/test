from app import db

async def create_or_get_movie(bot_id: int, code: str, title: str, caption: str = '', premium: int = 0):
    return await db.add_movie(bot_id, code, title, caption, premium)

async def add_part(movie_id: int, file_id: str, part_no: int = 1, source_chat_id: str | None = None, source_message_id: int | None = None):
    return await db.add_movie_part(movie_id, part_no, f'{part_no}-qism', file_id, source_chat_id, source_message_id)

async def find_by_code(bot_id: int, code: str):
    return await db.movie_by_code(bot_id, code)
