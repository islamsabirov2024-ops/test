"""Manual payment helpers: screenshot -> admin approve/reject."""

def payment_status_text(status: str) -> str:
    return {'pending': '⏳ Tekshiruvda', 'approved': '✅ Tasdiqlandi', 'rejected': '❌ Rad etildi'}.get(status, status)
