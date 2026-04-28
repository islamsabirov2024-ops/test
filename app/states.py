from aiogram.fsm.state import State, StatesGroup


# ================= CREATE BOT =================
class CreateBot(StatesGroup):
    bot_type = State()      # bot turini tanlash
    token = State()         # token kiritish (create + update uchun ishlatiladi)
    name = State()          # bot nomi
    tariff = State()        # tarif tanlash
    receipt = State()       # chek yuborish


# ================= MOVIE BOT =================
class MovieState(StatesGroup):
    add_code = State()          # kino kodi yozish
    add_content = State()       # kino content (forward/file)
    del_code = State()          # kino o‘chirish
    channel = State()           # kino kanal ulash
    broadcast = State()         # reklama yuborish
    sub_channel = State()       # majburiy obuna
    premium_code = State()      # premium kino


# ================= CLEANER =================
class CleanerState(StatesGroup):
    add_black = State()     # blacklist qo‘shish
    add_white = State()     # whitelist qo‘shish
    test = State()          # test rejim
