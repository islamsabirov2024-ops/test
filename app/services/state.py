# In-memory conversation states for the main bot.
WAITING = {}

def set_wait(user_id:int, action:str, data:str=''):
    WAITING[user_id] = {'action': action, 'data': data}

def pop_wait(user_id:int):
    return WAITING.pop(user_id, None)

def get_wait(user_id:int):
    return WAITING.get(user_id)
