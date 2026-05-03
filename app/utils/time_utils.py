import time
from datetime import datetime

def now_ts() -> int:
    return int(time.time())

def human(ts: int) -> str:
    return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')
