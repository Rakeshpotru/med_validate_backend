import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services import change_password_service as svc


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    """Provide an async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_current_user():
    return {"user_id": 123, "email": "testuser@example.com"}


# -----------------------------------------------------------
# ✅ SUCCESS CASE
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_success(monkeypatch, mock_current_user):
    user_record = {"user_id": 123, "password": "old_hashed", "is_temporary_password": True}

    async def fake_fetch_one(query):
        return user_record

    async def fake_execute(query):
        return True

    async def fake_is_password_reused(user_id, pwd):
        return False

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(svc.database, "execute", fake_execute)
    monkeypatch.setattr(svc, "verify_password", lambda old, hashed: True)
    monkeypatch.setattr(svc, "validate_password", lambda pwd: True)
    monkeypatch.setattr(svc, "is_password_reused", fake_is_password_reused)
    monkeypatch.setattr(svc, "get_password_hash", lambda pwd: "new_hashed_pwd")

    payload = svc.ChangePasswordRequest(
        old_password="Old@12345",
        new_password="NewPass@12345",
        confirm_password="NewPass@12345",
    )

    response = await svc.change_user_password(payload, mock_current_user)
    assert response["status_code"] == 200
    assert "success" in response["detail"].lower()


# -----------------------------------------------------------
# ❌ USER NOT FOUND
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_user_not_found(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        return None

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)

    payload = svc.ChangePasswordRequest(
        old_password="Old@123",
        new_password="New@123",
        confirm_password="New@123"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 404
    assert "user not found" in exc.value.detail.lower()


# -----------------------------------------------------------
# ❌ OLD PASSWORD INCORRECT
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_incorrect_old(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        return {"user_id": 123, "password": "stored_hashed"}

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(svc, "verify_password", lambda old, hashed: False)

    payload = svc.ChangePasswordRequest(
        old_password="WrongOld@123",
        new_password="New@123",
        confirm_password="New@123"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 400
    assert "old password is incorrect" in exc.value.detail.lower()


# -----------------------------------------------------------
# ❌ NEW PASSWORD TOO WEAK
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_weak_new_password(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        return {"user_id": 123, "password": "stored_hashed"}

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(svc, "verify_password", lambda old, hashed: True)
    monkeypatch.setattr(svc, "validate_password", lambda pwd: False)

    payload = svc.ChangePasswordRequest(
        old_password="Old@123",
        new_password="weak",
        confirm_password="weak"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 400
    assert "password must be at least" in exc.value.detail.lower()


# -----------------------------------------------------------
# ❌ NEW PASSWORD MISMATCH
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_mismatch(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        return {"user_id": 123, "password": "stored_hashed"}

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(svc, "verify_password", lambda old, hashed: True)
    monkeypatch.setattr(svc, "validate_password", lambda pwd: True)

    payload = svc.ChangePasswordRequest(
        old_password="Old@123",
        new_password="New@123",
        confirm_password="Diff@123"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 400
    assert "do not match" in exc.value.detail.lower()


# -----------------------------------------------------------
# ❌ PASSWORD REUSE DETECTED
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_reused(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        return {"user_id": 123, "password": "stored_hashed"}

    async def fake_is_password_reused(user_id, pwd):
        return True

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(svc, "verify_password", lambda old, hashed: True)
    monkeypatch.setattr(svc, "validate_password", lambda pwd: True)
    monkeypatch.setattr(svc, "is_password_reused", fake_is_password_reused)

    payload = svc.ChangePasswordRequest(
        old_password="Old@123",
        new_password="New@12345",
        confirm_password="New@12345"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 400
    assert "reuse" in exc.value.detail.lower()


# -----------------------------------------------------------
# 💥 INTERNAL SERVER ERROR (unexpected exception)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_change_password_unexpected_error(monkeypatch, mock_current_user):
    async def fake_fetch_one(query):
        raise Exception("DB crash")

    monkeypatch.setattr(svc.database, "fetch_one", fake_fetch_one)

    payload = svc.ChangePasswordRequest(
        old_password="Old@123",
        new_password="New@123",
        confirm_password="New@123"
    )

    with pytest.raises(HTTPException) as exc:
        await svc.change_user_password(payload, mock_current_user)

    assert exc.value.status_code == 500
    assert "unexpected error" in exc.value.detail.lower()
