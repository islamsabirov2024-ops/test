from aiogram.fsm.state import State, StatesGroup
class CreateBot(StatesGroup): token=State()
class AddMovie(StatesGroup): code=State(); media=State()
class DelMovie(StatesGroup): code=State()
class AddChannel(StatesGroup): title=State(); data=State()
class Broadcast(StatesGroup): text=State(); confirm=State()
