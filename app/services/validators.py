def is_valid_price(value: str, min_price: int = 1000, max_price: int = 1000000) -> bool:
    try:
        n = int(str(value).strip())
        return min_price <= n <= max_price
    except Exception:
        return False

def is_valid_days(value: str, min_days: int = 1, max_days: int = 3650) -> bool:
    try:
        n = int(str(value).strip())
        return min_days <= n <= max_days
    except Exception:
        return False
