from __future__ import annotations
import aiohttp
async def validate_bot_token(token:str):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f'https://api.telegram.org/bot{token}/getMe',timeout=20) as r:
                d=await r.json()
                return bool(d.get('ok')), d.get('result',{})
    except Exception:
        return False, {}
