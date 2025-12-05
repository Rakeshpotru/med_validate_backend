import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.transaction.users import users
from app.db.master.user_roles import user_roles_table


# --- Helper functions ---
async def insert_user(
    user_name="Test User",
    email="test@example.com",
    is_active=True,
    created_by="admin"
):
    query = (
        users.insert()
        .values(
            user_name=user_name,
            email=email,
            password="qwerty@123",
            is_active=is_active,
            created_by=created_by,
        )
        .returning(users.c.user_id)
    )
    return await database.fetch_val(query)


async def insert_role(role_name="Tester", is_active=True):
    query = (
        user_roles_table.insert()
        .values(role_name=role_name, is_active=is_active)
        .returning(user_roles_table.c.role_id)
    )
    return await database.fetch_val(query)


# --- GET /transaction/getAllUsers ---
@pytest.mark.anyio
async def test_get_all_users_success(async_client: AsyncClient):
    await insert_user("User1", "u1@example.com")
    await insert_user("User2", "u2@example.com")

    resp = await async_client.get("/transaction/getallusers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_code"] == 200
    assert data["message"] == "Users fetched successfully"
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 2
    assert all("email" in u for u in data["data"])


@pytest.mark.anyio
async def test_get_all_users_empty(async_client: AsyncClient):
    resp = await async_client.get("/transaction/getallusers")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status_code"] == 404
    assert data["message"] == "No users found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_users_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.t_users_service.database.fetch_all",
        side_effect=Exception("DB error"),
    )
    resp = await async_client.get("/transaction/getallusers")
    assert resp.status_code == 500
    data = resp.json()
    assert data["status_code"] == 500
    assert "Internal server error" in resp.json()["message"]


# --- POST /transaction/createUser ---
@pytest.mark.anyio
async def test_create_user_success(async_client: AsyncClient):
    role_id = await insert_role("Developer")
    payload = {
        "user_name": "NewUser",
        "email": "new@example.com",
        "role_id": role_id,
        "is_active": True,
        "created_by": 1,
    }
    resp = await async_client.post("/transaction/CreateUser", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status_code"] == 201
    assert "user_id" in data["data"]
    assert data["data"]["role_id"] == role_id


@pytest.mark.anyio
async def test_create_user_missing_role(async_client: AsyncClient):
    payload = {
        "user_name": "NoRole",
        "email": "norole@example.com",
        "is_active": True,
        "created_by": 1,
    }
    resp = await async_client.post("/transaction/CreateUser", json=payload)
    assert resp.status_code == 400
    assert "Either role_id" in resp.json()["message"]


@pytest.mark.anyio
async def test_create_user_email_conflict(async_client: AsyncClient):
    role_id = await insert_role("Manager")
    await insert_user("Dup", "dup@example.com")
    payload = {
        "user_name": "Dup",
        "email": "dup@example.com",
        "role_id": role_id,
        "is_active": True,
        "created_by": 1,
    }
    resp = await async_client.post("/transaction/CreateUser", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["message"]


@pytest.mark.anyio
async def test_create_user_invalid_role(async_client: AsyncClient):
    payload = {
        "user_name": "BadRole",
        "email": "br@example.com",
        "role_id": 9999,
        "is_active": True,
        "created_by": 1,
    }
    resp = await async_client.post("/transaction/CreateUser", json=payload)
    assert resp.status_code == 400
    assert "Invalid or inactive role" in resp.json()["message"]


@pytest.mark.anyio
async def test_create_user_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.t_users_service.database.fetch_val",
        side_effect=Exception("DB error"),
    )
    payload = {
        "user_name": "Error",
        "email": "err@example.com",
        "role_id": 1,
        "is_active": True,
        "created_by": 1,
    }
    resp = await async_client.post("/transaction/CreateUser", json=payload)
    assert resp.status_code == 500
    assert resp.json()["message"] == "Internal server error"


# --- PUT /transaction/updateUser ---
@pytest.mark.anyio
async def test_update_user_not_found(async_client: AsyncClient):
    payload = {
        "user_id": 9999,
        "user_name": "Ghost",
        "email": "ghost@example.com",
        "updated_by": 1,
    }
    resp = await async_client.put("/transaction/UpdateUser", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["message"]


@pytest.mark.anyio
async def test_update_user_email_conflict(async_client: AsyncClient):
    uid1 = await insert_user("First", "first@example.com")
    uid2 = await insert_user("Second", "second@example.com")
    payload = {
        "user_id": uid2,
        "user_name": "Second",
        "email": "first@example.com",
        "updated_by": 1,
    }
    resp = await async_client.put("/transaction/UpdateUser", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["message"]


@pytest.mark.anyio
async def test_update_user_success(async_client: AsyncClient):
    uid = await insert_user("Old", "old@example.com")
    payload = {
        "user_id": uid,
        "user_name": "New",
        "email": "new@example.com",
        "updated_by": 1,
    }
    resp = await async_client.put("/transaction/UpdateUser", json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == uid


@pytest.mark.anyio
async def test_update_user_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.t_users_service.database.fetch_one",
        side_effect=Exception("DB error"),
    )
    payload = {
        "user_id": 1,
        "user_name": "Err",
        "email": "err@example.com",
        "updated_by": 1,
    }
    resp = await async_client.put("/transaction/UpdateUser", json=payload)
    assert resp.status_code == 500
    assert resp.json()["message"] == "Internal server error"


# --- DELETE /transaction/deleteUser ---
@pytest.mark.anyio
async def test_delete_user_not_found(async_client: AsyncClient):
    payload = {"user_id": 9999, "updated_by": 1}
    resp = await async_client.request("DELETE", "/transaction/DeleteUser", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["message"]


@pytest.mark.anyio
async def test_delete_user_success(async_client: AsyncClient):
    uid = await insert_user("DeleteMe", "del@example.com")
    payload = {"user_id": uid, "updated_by": 1}
    resp = await async_client.request("DELETE", "/transaction/DeleteUser", json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == uid


@pytest.mark.anyio
async def test_delete_user_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.t_users_service.database.fetch_val",
        side_effect=Exception("DB error"),
    )
    payload = {"user_id": 1, "updated_by": 1}
    resp = await async_client.request("DELETE", "/transaction/DeleteUser", json=payload)
    assert resp.status_code == 500
    assert resp.json()["message"] == "Internal server error"
