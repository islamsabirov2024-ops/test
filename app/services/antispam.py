import time

class AntiSpam:
    def __init__(self):
        self.messages = {}
        self.blocked_until = {}

    def check(self, user_id: int, limit: int = 5, window: int = 3, block_seconds: int = 10) -> tuple[bool, int]:
        now = time.time()
        until = self.blocked_until.get(user_id, 0)
        if until > now:
            return False, int(until - now)
        arr = [x for x in self.messages.get(user_id, []) if now - x <= window]
        arr.append(now)
        self.messages[user_id] = arr
        if len(arr) > limit:
            self.blocked_until[user_id] = now + block_seconds
            return False, block_seconds
        return True, 0
