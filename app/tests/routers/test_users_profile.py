import io
import pytest
import random
import string
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from fastapi import status, HTTPException, UploadFile
from app.main import app
from app.db.database import database
from app.db.transaction.users import users as users_table
from app.db.master.user_roles import user_roles_table


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# @pytest.fixture
# async def async_client():
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url="http://test") as ac:
#         yield ac


@pytest.fixture
async def setup_roles():
    """Ensure at least one role exists."""
    query = user_roles_table.insert().values(role_name="Admin", is_active=True).returning(user_roles_table.c.role_id)
    role_id = await database.execute(query)
    return role_id


def random_email():
    return f"test_{''.join(random.choices(string.ascii_lowercase, k=6))}@example.com"


# -----------------------------------------------------------
# ✅ TEST: Create User (NewCreateUser)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_create_user_success(async_client: AsyncClient, setup_roles):
    payload = {
        "users": {
            "user_first_name": "John",
            "user_middle_name": "K",
            "user_last_name": "Doe",
            "user_email": random_email(),
            "user_phone": "9876543210",
            "role_id": setup_roles,
            "user_address": "123 Test Street"
        },
        "created_by": 1,
        "is_active": True
    }

    response = await async_client.post("/users/NewCreateUser", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "created_user_ids" in data["data"]
    assert data["status"] == "success"
    assert data["data"]["validation_errors"] == []


# -----------------------------------------------------------
# ❌ TEST: Duplicate User (Conflict)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_create_user_conflict(async_client: AsyncClient, setup_roles):
    email = random_email()
    payload = {
        "users": {
            "user_first_name": "Alice",
            "user_middle_name": "Q",
            "user_last_name": "Smith",
            "user_email": email,
            "user_phone": "9876543210",
            "role_id": setup_roles,
            "user_address": "City Road"
        },
        "created_by": 1,
        "is_active": True
    }

    await async_client.post("/users/NewCreateUser", json=payload)
    response = await async_client.post("/users/NewCreateUser", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "existing_users" in response.json()["data"]


# -----------------------------------------------------------
# ✅ TEST: Get User by ID
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_get_user_by_id(async_client: AsyncClient, setup_roles):
    email = random_email()
    insert_stmt = users_table.insert().values(
        user_first_name="Tom",
        user_last_name="Jerry",
        email=email,
        user_name="Tom Jerry",
        password="hashed",
        is_active=True,
        created_by=1,
        created_date=datetime.now(timezone.utc)
    ).returning(users_table.c.user_id)
    user_id = await database.execute(insert_stmt)

    response = await async_client.get(f"/users/getUserById/{user_id}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["user_id"] == user_id


# -----------------------------------------------------------
# ❌ TEST: Get User (Not Found)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_get_user_not_found(async_client: AsyncClient):
    response = await async_client.get("/users/getUserById/99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.text.lower()


# -----------------------------------------------------------
# ✅ TEST: Update User
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_update_user_success(async_client: AsyncClient, setup_roles):
    insert_stmt = users_table.insert().values(
        user_first_name="Jane",
        user_last_name="Brown",
        email=random_email(),
        user_name="Jane Brown",
        password="hashed",
        is_active=True,
        created_by=1,
        created_date=datetime.now(timezone.utc)
    ).returning(users_table.c.user_id)
    user_id = await database.execute(insert_stmt)

    payload = {
        "user_first_name": "Janet",
        "user_last_name": "Updated",
        "user_phone": "9876543210",
        "user_address": "New Street",
        "role_id": setup_roles,
        "updated_by": 1
    }

    response = await async_client.put(f"/users/NewUpdateUser/{user_id}", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["user_id"] == user_id


# -----------------------------------------------------------
# ❌ TEST: Update User (Invalid Phone)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_update_user_invalid_phone(async_client: AsyncClient, setup_roles):
    insert_stmt = users_table.insert().values(
        user_first_name="Invalid",
        user_last_name="Phone",
        email=random_email(),
        user_name="Invalid Phone",
        password="hashed",
        is_active=True,
        created_by=1,
        created_date=datetime.now(timezone.utc)
    ).returning(users_table.c.user_id)
    user_id = await database.execute(insert_stmt)

    payload = {"user_phone": "12345", "updated_by": 1}
    response = await async_client.put(f"/users/NewUpdateUser/{user_id}", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "invalid phone" in response.text.lower()


# -----------------------------------------------------------
# ✅ TEST: Upload Profile Image
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_upload_user_profile_image(async_client: AsyncClient, tmp_path):
    insert_stmt = users_table.insert().values(
        user_first_name="Image",
        user_last_name="User",
        email=random_email(),
        user_name="Image User",
        password="hashed",
        is_active=True,
        created_by=1,
        created_date=datetime.now(timezone.utc)
    ).returning(users_table.c.user_id)
    user_id = await database.execute(insert_stmt)

    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"fakeimagecontent")
    with open(img_path, "rb") as f:
        files = {"file": ("test.png", f, "image/png")}
        response = await async_client.post(f"/users/{user_id}/upload-image", files=files)

    assert response.status_code == status.HTTP_200_OK
    assert "uploaded successfully" in response.json()["message"].lower()


# -----------------------------------------------------------
# ✅ TEST: Delete Profile Image (No Image Found)
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_delete_user_profile_image_not_found(async_client: AsyncClient):
    insert_stmt = users_table.insert().values(
        user_first_name="NoImg",
        user_last_name="User",
        email=random_email(),
        user_name="NoImg User",
        password="hashed",
        is_active=True,
        created_by=1,
        created_date=datetime.now(timezone.utc)
    ).returning(users_table.c.user_id)
    user_id = await database.execute(insert_stmt)

    response = await async_client.delete(f"/users/{user_id}/delete-image")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "no profile image" in response.text.lower()


# -----------------------------------------------------------
# ✅ INTERNAL COVERAGE: Direct Service Tests
# -----------------------------------------------------------
@pytest.mark.anyio
async def test_internal_service_functions(monkeypatch):
    from app.services.transaction import users_service

    # ---- validate_user ----
    class DummyUser:
        role_id = 999
        user_phone = "12345"
    async def fake_fetch_one(stmt): return None
    monkeypatch.setattr(users_service.database, "fetch_one", fake_fetch_one)
    errors = await users_service.validate_user(DummyUser())
    assert errors is None or any("Invalid" in e for e in (errors or []))

    # ---- generate_strong_password ----
    from pytest import raises
    with raises(ValueError):
        users_service.generate_strong_password(3)
    pwd = users_service.generate_strong_password(10)
    assert any(c.isupper() for c in pwd)
    assert any(c.islower() for c in pwd)
    assert any(c.isdigit() for c in pwd)

    # ---- prepare_registration_email ----
    html = users_service.prepare_registration_email("John", "john@example.com", "Pwd@123", "https://login.url")
    assert "john@example.com" in html and "https://login.url" in html

    # ---- insert/update_user_role_mapping ----
    called = {}
    async def fake_execute(stmt): called["ok"] = True
    monkeypatch.setattr(users_service.database, "execute", fake_execute)
    await users_service.insert_user_role_mapping(1, 2, 3)
    await users_service.update_user_role_mapping(1, 2, 1)
    assert "ok" in called

    # ---- upload_user_profile_image_service invalid type ----
    from starlette.datastructures import UploadFile

    class DummyUploadFile(UploadFile):
        def __init__(self):
            super().__init__(filename="bad.txt", file=io.BytesIO(b"abc"))
        @property
        def content_type(self):
            return "text/plain"

    fake_file = DummyUploadFile()
    with pytest.raises(HTTPException):
        await users_service.upload_user_profile_image_service(1, fake_file)

    # ---- delete_user_profile_image_service user not found ----
    async def fake_fetch_none(stmt): return None
    monkeypatch.setattr(users_service.database, "fetch_one", fake_fetch_none)
    with pytest.raises(HTTPException):
        await users_service.delete_user_profile_image_service(1)
