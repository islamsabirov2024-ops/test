from aiogram.fsm.state import State, StatesGroup
class CreateBot(StatesGroup):
    bot_type=State(); token=State(); name=State(); tariff=State(); receipt=State()
class MovieState(StatesGroup):
    add_code=State(); add_content=State(); del_code=State(); channel=State(); broadcast=State(); sub_channel=State(); premium_code=State()
class CleanerState(StatesGroup):
    add_black=State(); add_white=State(); test=State()
