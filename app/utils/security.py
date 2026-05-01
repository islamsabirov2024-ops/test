from app.config import SUPER_ADMIN_ID


def is_super_admin(user_id: int) -> bool:
    return int(user_id or 0) == int(SUPER_ADMIN_ID)
