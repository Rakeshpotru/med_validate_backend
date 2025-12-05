import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta, UTC
from sqlalchemy import select

from app.db.database import database

from app.db.transaction.users import users as users_table
from app.db.transaction.user_password_history import user_password_history
from app.db.transaction.user_otp import user_otp
from app.security import get_password_hash
from app.utils.validations import generate_otp


# ─────────────────────────────
# Helper Functions
# ─────────────────────────────

async def forgot_password(client: AsyncClient, email: str):
    """Trigger the forgot-password endpoint."""
    return await client.post("/forgot-password", json={"email": email})


async def verify_otp(client: AsyncClient, user_id: int, otp: str):
    """Verify OTP endpoint."""
    return await client.post("/verify-otp", json={"user_id": user_id, "otp": otp})


async def reset_password(client: AsyncClient, user_id: int, new_pw: str, confirm_pw: str):
    """Reset password endpoint."""
    return await client.post("/reset-password", json={
        "user_id": user_id,
        "new_password": new_pw,
        "confirm_password": confirm_pw
    })


# ─────────────────────────────
# Forgot Password Tests
# ─────────────────────────────

@pytest.mark.anyio
async def test_forgot_password_valid_email(async_client: AsyncClient, registered_user: dict):
    """
    Test: Forgot password should succeed for valid email and create OTP in DB.
    """
    response = await forgot_password(async_client, registered_user["email"])

    assert response.status_code == 200
    assert "otp" in response.json()["message"].lower() or "sent" in response.json()["message"].lower()

    query = select(user_otp).where(user_otp.c.user_id == registered_user["user_id"])
    otp_entry = await database.fetch_one(query)

    assert otp_entry is not None
    assert len(otp_entry["otp"]) > 3
    assert otp_entry["otp_expiry_date"].replace(tzinfo=None) > datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.anyio
async def test_forgot_password_invalid_email(async_client: AsyncClient):
    """
    Test: Forgot password with unregistered email should fail.
    """
    response = await forgot_password(async_client, "nonexist@example.com")

    assert response.status_code in [400, 404]
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_forgot_password_inactive_user(async_client: AsyncClient, registered_user):
    """
    Test: Forgot password should fail for inactive users.
    """
    await database.execute(users_table.update().where(
        users_table.c.user_id == registered_user["user_id"]
    ).values(is_active=False))

    response = await forgot_password(async_client, registered_user["email"])

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_forgot_password_unverified_user(async_client: AsyncClient, registered_user):
    """
    Test: Forgot password should fail for users with temporary passwords (unverified).
    """
    await database.execute(users_table.update().where(
        users_table.c.user_id == registered_user["user_id"]
    ).values(is_temporary_password=True))

    response = await forgot_password(async_client, registered_user["email"])

    assert response.status_code == 400
    assert "verify" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_forgot_password_missing_email(async_client: AsyncClient):
    """
    Test: Forgot password should return 422 for missing email field.
    """
    response = await async_client.post("/forgot-password", json={})
    assert response.status_code == 422


# ─────────────────────────────
# OTP Verification Tests
# ─────────────────────────────

@pytest.mark.anyio
async def test_verify_correct_otp(async_client: AsyncClient, registered_user):
    """
    Test: OTP verification succeeds with correct OTP.
    """
    otp = generate_otp()
    expiry = datetime.now(UTC) + timedelta(minutes=10)

    await database.execute(user_otp.insert().values(
        user_id=registered_user["user_id"],
        otp=otp,
        otp_expiry_date=expiry,
        created_date=datetime.now(UTC)
    ))

    response = await verify_otp(async_client, registered_user["user_id"], otp)

    assert response.status_code == 200
    assert "verified" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_verify_expired_otp(async_client: AsyncClient, registered_user):
    """
    Test: Expired OTP should be rejected.
    """
    otp = "123456"
    expiry = datetime.now(UTC) - timedelta(minutes=1)

    await database.execute(user_otp.insert().values(
        user_id=registered_user["user_id"],
        otp=otp,
        otp_expiry_date=expiry,
        created_date=datetime.now(UTC)
    ))

    response = await verify_otp(async_client, registered_user["user_id"], otp)

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_verify_otp_empty_input(async_client: AsyncClient, registered_user):
    """
    Test: Empty OTP input should return 400.
    """
    response = await verify_otp(async_client, registered_user["user_id"], "   ")

    assert response.status_code == 400
    assert "otp" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_verify_otp_not_found(async_client: AsyncClient, registered_user):
    """
    Test: OTP not found should return error.
    """
    await database.execute(user_otp.delete().where(user_otp.c.user_id == registered_user["user_id"]))

    response = await verify_otp(async_client, registered_user["user_id"], "000000")

    assert response.status_code == 400
    assert "no otp generated" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_verify_incorrect_otp(async_client: AsyncClient, registered_user):
    """
    Test: Incorrect OTP should be rejected.
    """
    await database.execute(user_otp.insert().values(
        user_id=registered_user["user_id"],
        otp="123456",
        otp_expiry_date=datetime.now(UTC) + timedelta(minutes=10),
        created_date=datetime.now(UTC)
    ))

    response = await verify_otp(async_client, registered_user["user_id"], "999999")

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


# ─────────────────────────────
# Password Reset Tests
# ─────────────────────────────

@pytest.mark.anyio
async def test_reset_password_success(async_client: AsyncClient, registered_user):
    """
    Test: Password reset should succeed with valid inputs.
    """
    new_password = "NewStrongPass1!"

    response = await reset_password(async_client, registered_user["user_id"], new_password, new_password)

    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()


@pytest.mark.anyio
async def test_reset_password_weak_password(async_client: AsyncClient, registered_user):
    """
    Test: Weak passwords should be rejected.
    """
    weak_password = "123"

    response = await reset_password(async_client, registered_user["user_id"], weak_password, weak_password)

    assert response.status_code == 400
    assert "password does not meet strength requirements" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_password_reuse(async_client: AsyncClient, registered_user):
    """
    Test: Passwords used in history should not be reused.
    """
    reused_password = "OldPassword1!"

    await database.execute(user_password_history.insert().values(
        user_id=registered_user["user_id"],
        old_password=get_password_hash(reused_password),
        password_changed_date=datetime.now(UTC)
    ))

    response = await reset_password(async_client, registered_user["user_id"], reused_password, reused_password)

    assert response.status_code == 400
    assert "reuse" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_reset_password_mismatch(async_client: AsyncClient, registered_user):
    """
    Test: Mismatched new and confirm password fields should fail.
    """
    response = await reset_password(async_client, registered_user["user_id"], "Password123!", "Password456!")

    assert response.status_code == 400
    assert "match" in response.json()["detail"].lower()
