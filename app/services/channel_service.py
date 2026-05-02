async def normalize_channel(raw: str) -> str:
    raw = (raw or '').strip()
    if raw.startswith('https://t.me/'):
        return '@' + raw.rstrip('/').split('/')[-1]
    return raw

async def is_telegram_checkable(raw: str) -> bool:
    raw = (raw or '').strip()
    return raw.startswith('@') or raw.startswith('-100') or 't.me/' in raw
