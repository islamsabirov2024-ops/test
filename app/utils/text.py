def money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ") + " so'm"


def short_token(token: str) -> str:
    if not token:
        return "-"
    return token[:8] + "..." + token[-5:]


def clean_code(text: str) -> str:
    return (text or "").strip().lower()


def is_menu_text(text: str) -> bool:
    prefixes = ("📊", "📨", "🎬", "👮", "⚙️", "🔐", "💳", "💎", "📣", "🔙", "🏠", "🤖", "🧹", "➕", "📋", "🗑", "✅", "❌", "▶️", "⏸")
    return bool(text and text.strip().startswith(prefixes))
