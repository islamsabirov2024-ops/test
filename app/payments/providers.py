PROVIDERS = ('Payme', 'Click', 'Karta', 'Humo')

def is_supported_provider(name: str) -> bool:
    return (name or '').strip().lower() in {p.lower() for p in PROVIDERS}
