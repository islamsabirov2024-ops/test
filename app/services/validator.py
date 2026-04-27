import aiohttp
async def validate_bot_token(token:str):
    token=(token or '').strip()
    if ':' not in token or len(token)<20:
        return False, {}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f'https://api.telegram.org/bot{token}/getMe', timeout=15) as r:
                data=await r.json()
                return bool(data.get('ok')), data.get('result') or {}
    except Exception:
        return False, {}
