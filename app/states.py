from aiogram.fsm.state import State, StatesGroup
class CreateBot(StatesGroup):
    bot_type=State(); token=State(); name=State()
