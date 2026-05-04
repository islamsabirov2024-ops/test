import re

def parse_tme_link(text: str):
    """Return (chat, message_id) from t.me link when possible."""
    text = (text or '').strip()
    m = re.search(r't\.me/(?:c/)?([^/]+)/([0-9]+)', text)
    if not m:
        return None
    chat = m.group(1)
    msg_id = int(m.group(2))
    if chat.isdigit():
        chat = '-100' + chat
    elif not chat.startswith('@'):
        chat = '@' + chat
    return chat, msg_id
