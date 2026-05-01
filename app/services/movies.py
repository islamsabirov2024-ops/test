from app import database as db
from app.utils.text import clean_code

async def save_movie(bot_id:int, code:str, title:str='', file_id:str='', source_chat_id:str='', source_message_id:int=0, premium:int=0):
    await db.add_movie(bot_id, clean_code(code), title, file_id, source_chat_id, source_message_id, premium)

async def find_movie(bot_id:int, code:str):
    return await db.get_movie(bot_id, clean_code(code))
