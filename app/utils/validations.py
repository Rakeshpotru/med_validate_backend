import re
import secrets

from fastapi import HTTPException
from app.db.database import database
from app.db.transaction.user_password_history import user_password_history
from app.security import verify_password


def generate_otp() -> str:
    """
    Generate a secure 4-digit numeric OTP.
    """
    return ''.join(secrets.choice('0123456789') for _ in range(4))


async def is_password_reused(user_id: int, plain_password: str) -> bool:
    """
    Check if the given password has been used in the last 5 password changes.
    """
    query = (
        user_password_history.select()
        .where(user_password_history.c.user_id == user_id)
        .order_by(user_password_history.c.password_changed_date.desc())
        .limit(5)
    )
    recent_passwords = await database.fetch_all(query)

    for record in recent_passwords:
        if verify_password(plain_password, record["old_password"]):
            return True
    return False


def validate_password(password: str) -> bool:
    """
    Validate password strength:
    - At least 12 characters
    - At least one lowercase, uppercase, digit, and special character
    """
    if len(password) < 12:
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[\W_]', password):
        return False
    return True


def validate_user_account(user: dict):
    """
    Raise appropriate HTTP exceptions based on user account status.
    """
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is inactive")
    if user["is_temporary_password"]:
        raise HTTPException(status_code=400, detail="Account is not verified. Please verify it first.")
