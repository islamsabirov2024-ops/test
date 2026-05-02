import asyncio
import time

async def simple_scheduler(interval_seconds: int, callback):
    while True:
        await callback()
        await asyncio.sleep(interval_seconds)

def now_ts() -> int:
    return int(time.time())
