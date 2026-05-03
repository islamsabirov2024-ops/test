from dataclasses import dataclass

@dataclass
class TariffModel:
    id: int
    name: str
    days: int
    price: int
    active: bool = True

@dataclass
class MovieModel:
    id: int
    bot_id: int
    code: str
    title: str
    premium: bool = False
