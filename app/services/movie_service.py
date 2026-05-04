from app import db

async def resolve_movie_by_code(bot_id: int, code: str):
    return await db.movie_by_code(bot_id, code.strip())

async def next_part_number(movie_id: int) -> int:
    parts = await db.movie_parts(movie_id)
    return len(parts) + 1
