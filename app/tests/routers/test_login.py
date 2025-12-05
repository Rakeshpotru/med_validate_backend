import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, timezone

# --- Helper class to simulate SQLAlchemy row ---
class MockRow:
    def __init__(self, data):
        self._mapping = data

# --- Helper function ---
async def login_request(async_client: AsyncClient, email: str, password: str):
    payload = {"user_email": email, "user_password": password}
    return await async_client.post("/auth/login", json=payload)


# --- TESTS ---
@pytest.mark.anyio
async def test_login_success(mocker, async_client: AsyncClient):
    """✅ Successful login should return JWT token and user info"""
    user = {
        "user_id": 1,
        "user_name": "John Doe",
        "email": "john@example.com",
        "password": "$2b$12$hashedpassword",
        "login_failed_count": 0,
        "is_user_locked": False,
        "user_locked_time": None,
        "is_temporary_password": False,
        "password_validity_date": None,
    }

    # Mock all dependencies
    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=MockRow(user)))
    mocker.patch("app.services.login_service.verify_password", return_value=True)
    mocker.patch("app.services.login_service.create_access_token", AsyncMock(return_value="fake-jwt-token"))
    mocker.patch("app.services.login_service.get_user_role", AsyncMock(return_value={"id": 1, "name": "Admin"}))
    mocker.patch("app.services.login_service.reset_user_login_state", AsyncMock())
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())
    mocker.patch("app.db.database.database.execute", AsyncMock())

    response = await login_request(async_client, "john@example.com", "password123")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Login successful"
    assert data["access_token"] == "fake-jwt-token"
    assert data["user_role"] == "Admin"
    assert data["user_id"] == 1
    assert data["name"] == "John Doe"


@pytest.mark.anyio
async def test_login_invalid_email(mocker, async_client: AsyncClient):
    """❌ Invalid email should return 403"""
    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=None))
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())

    response = await login_request(async_client, "wrong@example.com", "password123")
    data = response.json()

    assert response.status_code == 403
    assert data["status_code"] == 403
    assert data["message"] == "Invalid credentials"


@pytest.mark.anyio
async def test_login_invalid_password_then_lock(mocker, async_client: AsyncClient):
    """❌ Wrong password increases failed attempts and may lock account"""
    user = {
        "user_id": 1,
        "user_name": "John Doe",
        "email": "john@example.com",
        "password": "$2b$12$hashedpassword",
        "login_failed_count": 4,  # already failed 4 times
        "is_user_locked": False,
        "user_locked_time": None,
        "is_temporary_password": False,
        "password_validity_date": None,
    }

    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=MockRow(user)))
    mocker.patch("app.services.login_service.verify_password", return_value=False)
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())
    mocker.patch("app.db.database.database.execute", AsyncMock())

    response = await login_request(async_client, "john@example.com", "wrongpassword")
    data = response.json()

    assert response.status_code in [401, 403]  # may be locked now
    assert "Invalid credentials" in data["message"] or "Account locked" in data["message"]


@pytest.mark.anyio
async def test_login_locked_account(mocker, async_client: AsyncClient):
    """❌ Locked account should return lock message"""
    locked_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    user = {
        "user_id": 1,
        "user_name": "John Doe",
        "email": "john@example.com",
        "password": "$2b$12$hashedpassword",
        "login_failed_count": 5,
        "is_user_locked": True,
        "user_locked_time": locked_time,
        "is_temporary_password": False,
        "password_validity_date": None,
    }

    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=MockRow(user)))
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())

    response = await login_request(async_client, "john@example.com", "password123")
    data = response.json()

    assert response.status_code == 403
    assert "Account temporarily locked" in data["message"]


@pytest.mark.anyio
async def test_login_password_expired(mocker, async_client: AsyncClient):
    """⚠️ Expired password should set password_expired flag"""
    expired_date = datetime.now(timezone.utc) - timedelta(days=100)
    user = {
        "user_id": 1,
        "user_name": "Jane Smith",
        "email": "jane@example.com",
        "password": "$2b$12$hashedpassword",
        "login_failed_count": 0,
        "is_user_locked": False,
        "user_locked_time": None,
        "is_temporary_password": False,
        "password_validity_date": expired_date,
    }

    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 90 if key=="PASSWORD_EXPIRY_DAYS" else 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=MockRow(user)))
    mocker.patch("app.services.login_service.verify_password", return_value=True)
    mocker.patch("app.services.login_service.create_access_token", AsyncMock(return_value="expired-jwt-token"))
    mocker.patch("app.services.login_service.get_user_role", AsyncMock(return_value={"id": 2, "name": "User"}))
    mocker.patch("app.services.login_service.reset_user_login_state", AsyncMock())
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())
    mocker.patch("app.db.database.database.execute", AsyncMock())

    response = await login_request(async_client, "jane@example.com", "password123")
    data = response.json()

    assert response.status_code == 200
    assert data["password_expired"] is True
    assert data["access_token"] == "expired-jwt-token"


@pytest.mark.anyio
async def test_login_temp_password(mocker, async_client: AsyncClient):
    """⚠️ Temporary password should return temp_password=True"""
    user = {
        "user_id": 2,
        "user_name": "Temp User",
        "email": "temp@example.com",
        "password": "$2b$12$hashedpassword",
        "login_failed_count": 0,
        "is_user_locked": False,
        "user_locked_time": None,
        "is_temporary_password": True,
        "password_validity_date": None,
    }

    mocker.patch(
        "app.services.login_service.get_config_value",
        AsyncMock(side_effect=lambda key, type_: 5 if key=="MAX_FAILED_ATTEMPTS" else 20)
    )
    mocker.patch("app.services.login_service.fetch_user_by_email", AsyncMock(return_value=MockRow(user)))
    mocker.patch("app.services.login_service.verify_password", return_value=True)
    mocker.patch("app.services.login_service.create_access_token", AsyncMock(return_value="temp-jwt-token"))
    mocker.patch("app.services.login_service.get_user_role", AsyncMock(return_value={"id": 3, "name": "TempRole"}))
    mocker.patch("app.services.login_service.reset_user_login_state", AsyncMock())
    mocker.patch("app.services.login_service.log_user_audit", AsyncMock())
    mocker.patch("app.db.database.database.execute", AsyncMock())

    response = await login_request(async_client, "temp@example.com", "password123")
    data = response.json()

    assert response.status_code == 200
    assert data["temp_password"] is True
    assert data["access_token"] == "temp-jwt-token"
