def clamp_tariff_price(value: int) -> int:
    return max(1000, min(1000000, int(value)))

def format_uzs(value: int) -> str:
    return f"{int(value):,}".replace(',', ' ')
