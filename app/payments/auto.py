"""Auto payment helpers for Payme/Click.
Real merchant keys are read from environment and webhook handlers can approve payment by order/payment id."""
import os

def auto_pay_enabled() -> bool:
    return os.getenv('AUTO_PAYMENT_ENABLED','0').lower() in {'1','true','yes','on'}

def get_provider_url(provider: str, amount: int, order_id: int) -> str:
    provider=provider.lower()
    base=os.getenv(f'{provider.upper()}_PAYMENT_URL','').strip()
    if not base:
        return ''
    sep='&' if '?' in base else '?'
    return f'{base}{sep}amount={int(amount)}&order_id={int(order_id)}'
