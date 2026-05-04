def fmt_money(value) -> str:
    try:
        return f"{int(value):,}".replace(',', ' ')
    except Exception:
        return str(value)
