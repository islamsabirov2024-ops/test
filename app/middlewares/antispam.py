import time
from collections import defaultdict, deque

class AntiSpamStore:
    def __init__(self, limit: int = 5, window: int = 3, block_seconds: int = 10):
        self.limit = limit
        self.window = window
        self.block_seconds = block_seconds
        self.events = defaultdict(deque)
        self.blocked_until = {}

    def check(self, user_id: int) -> tuple[bool, int]:
        now = time.time()
        until = self.blocked_until.get(user_id, 0)
        if until > now:
            return False, int(until - now)
        q = self.events[user_id]
        while q and now - q[0] > self.window:
            q.popleft()
        q.append(now)
        if len(q) > self.limit:
            self.blocked_until[user_id] = now + self.block_seconds
            q.clear()
            return False, self.block_seconds
        return True, 0
