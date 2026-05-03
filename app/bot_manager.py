"""Child bot manager.

Asosiy ishchi logika app/main.py ichida start_child/stop_child funksiyalarida.
Bu modul keyingi kengaytirish uchun alohida saqlandi.
"""

class BotManager:
    def __init__(self):
        self.tasks = {}

    def running_count(self) -> int:
        return len(self.tasks)
