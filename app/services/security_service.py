def mask_token(token: str) -> str:
    token = token or ''
    if len(token) < 12:
        return '***'
    return token[:6] + '...' + token[-4:]
