import re
from typing import Optional, Tuple


def parse_tme_link(text: str) -> Optional[Tuple[str, int]]:
    if not text:
        return None
    m = re.search(r"t\.me/(c/\d+|[A-Za-z0-9_]+)/([0-9]+)", text)
    if not m:
        return None
    chat = m.group(1)
    msg_id = int(m.group(2))
    if chat.startswith("c/"):
        internal = chat.split("/", 1)[1]
        return (f"-100{internal}", msg_id)
    return ("@" + chat, msg_id)


def has_link_or_ad(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(x in low for x in ["http://", "https://", "t.me/", "@", "www."])
