import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.user_roles import user_roles_table


# --- Helper functions ---
async def get_all_user_roles_request(async_client: AsyncClient):
    """Send GET request to fetch all user roles."""
    return await async_client.get("/master/getAllUserRoles")


async def insert_user_role(role_name="Test Role", is_active=True):
    """Insert a role into DB."""
    query = user_roles_table.insert().values(
        role_name=role_name,
        is_active=is_active
    )
    await database.execute(query)

async def create_user_role_request(async_client: AsyncClient, role_name: str, is_active: bool = True):
    """Send POST request to create a user role."""
    payload = {"role_name": role_name, "is_active": is_active}
    return await async_client.post("/master/createUserRole", json=payload)


async def insert_user_role(role_name="Test Role", is_active=True):
    """Insert a role into DB directly."""
    query = user_roles_table.insert().values(role_name=role_name, is_active=is_active)
    return await database.execute(query)

async def update_user_role_request(async_client: AsyncClient, role_id: int, role_name: str):
    """Send PUT request to update a user role."""
    payload = {"role_id": role_id, "role_name": role_name}
    return await async_client.put("/master/updateUserRole", json=payload)


async def insert_user_role(role_name="Test Role", is_active=True):
    """Insert role directly into DB and return role_id."""
    query = user_roles_table.insert().values(role_name=role_name, is_active=is_active)
    return await database.execute(query)

async def delete_user_role_request(async_client: AsyncClient, role_id: int):
    """Send DELETE request to delete a role."""
    payload = {"role_id": role_id}
    return await async_client.request("DELETE", "/master/deleteUserRole", json=payload)

# --- Test cases ---
@pytest.mark.anyio
async def test_get_all_user_roles_success(async_client: AsyncClient):
    await insert_user_role(role_name="Admin")
    await insert_user_role(role_name="Editor")

    response = await get_all_user_roles_request(async_client)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "User roles fetched successfully"
    assert len(data["data"]) == 2
    assert all("role_name" in role for role in data["data"])


@pytest.mark.anyio
async def test_get_all_user_roles_empty(async_client: AsyncClient):
    # No roles in DB
    response = await get_all_user_roles_request(async_client)

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No user roles found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_user_roles_only_inactive(async_client: AsyncClient):
    await insert_user_role(role_name="Viewer", is_active=False)

    response = await get_all_user_roles_request(async_client)

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No user roles found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_user_roles_internal_server_error(mocker, async_client: AsyncClient):
    # Patch fetch_all to raise an error
    mocker.patch("app.services.user_roles_service.database.fetch_all", side_effect=Exception("DB error"))

    response = await get_all_user_roles_request(async_client)

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


@pytest.mark.anyio
async def test_create_user_role_success(async_client: AsyncClient):
    """Should create a new role when not exists."""
    response = await create_user_role_request(async_client, "Admin")

    assert response.status_code == 201
    data = response.json()
    assert data["status_code"] == 201
    assert data["message"] == "User role created successfully"
    assert data["data"]["role_name"] == "Admin"
    assert "role_id" in data["data"]


@pytest.mark.anyio
async def test_create_user_role_missing_name(async_client: AsyncClient):
    """Should return 400 if role_name is missing/empty."""
    response = await create_user_role_request(async_client, "")

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "Role name is required"


@pytest.mark.anyio
async def test_create_user_role_conflict(async_client: AsyncClient):
    """Should return 409 if role already exists and active."""
    await insert_user_role("Manager", is_active=True)

    response = await create_user_role_request(async_client, "Manager")

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]


@pytest.mark.anyio
async def test_create_user_role_activate_inactive(async_client: AsyncClient):
    """Should activate inactive role if exists."""
    role_id = await insert_user_role("Viewer", is_active=False)

    response = await create_user_role_request(async_client, "Viewer")

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert "activated successfully" in data["message"]
    assert data["data"]["role_id"] == role_id
    assert data["data"]["role_name"] == "Viewer"


@pytest.mark.anyio
async def test_create_user_role_internal_server_error(mocker, async_client: AsyncClient):
    """Should return 500 on exception."""
    mocker.patch("app.services.user_roles_service.database.fetch_one", side_effect=Exception("DB error"))

    response = await create_user_role_request(async_client, "ErrorRole")

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []

@pytest.mark.anyio
async def test_update_user_role_missing_id(async_client: AsyncClient):
    """Should return 422 if role_id is missing (FastAPI validation)."""
    response = await async_client.put("/master/updateUserRole", json={"role_name": "New Name"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_update_user_role_missing_name(async_client: AsyncClient):
    """Should return 400 if role_name missing."""
    role_id = await insert_user_role("Old Name")
    response = await update_user_role_request(async_client, role_id, "")
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Role name is required"


@pytest.mark.anyio
async def test_update_user_role_not_found(async_client: AsyncClient):
    """Should return 404 if role_id not in DB."""
    response = await update_user_role_request(async_client, 9999, "Nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "Role not found"


@pytest.mark.anyio
async def test_update_user_role_conflict(async_client: AsyncClient):
    """Should return 409 if another active role with same name exists."""
    role1_id = await insert_user_role("Admin", is_active=True)
    role2_id = await insert_user_role("Manager", is_active=True)

    response = await update_user_role_request(async_client, role2_id, "Admin")
    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["message"]


@pytest.mark.anyio
async def test_update_user_role_success(async_client: AsyncClient):
    """Should update role name successfully."""
    role_id = await insert_user_role("Editor")
    response = await update_user_role_request(async_client, role_id, "Content Editor")

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Role updated successfully"
    assert data["data"]["role_id"] == role_id
    assert data["data"]["role_name"] == "Content Editor"


@pytest.mark.anyio
async def test_update_user_role_internal_error(mocker, async_client: AsyncClient):
    """Should return 500 on exception."""
    mocker.patch("app.services.user_roles_service.database.fetch_one", side_effect=Exception("DB error"))

    response = await update_user_role_request(async_client, 1, "Broken")
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"

@pytest.mark.anyio
async def test_delete_user_role_missing_id(async_client: AsyncClient):
    """Should return 422 if role_id is missing (FastAPI validation)."""
    response = await async_client.request("DELETE", "/master/deleteUserRole", json={})
    assert response.status_code == 422  # FastAPI validation kicks in


@pytest.mark.anyio
async def test_delete_user_role_not_found(async_client: AsyncClient):
    """Should return 404 if role_id not in DB."""
    response = await delete_user_role_request(async_client, 9999)
    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "Role not found"


@pytest.mark.anyio
async def test_delete_user_role_already_inactive(async_client: AsyncClient):
    """Should return 409 if role already inactive."""
    role_id = await insert_user_role("Inactive Role", is_active=False)

    response = await delete_user_role_request(async_client, role_id)
    assert response.status_code == 409
    data = response.json()
    assert data["message"] == "Role is already inactive"
    assert data["data"] == []


@pytest.mark.anyio
async def test_delete_user_role_success(async_client: AsyncClient):
    """Should mark role as inactive successfully."""
    role_id = await insert_user_role("Active Role", is_active=True)

    response = await delete_user_role_request(async_client, role_id)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Role inactivated successfully"
    assert data["data"]["role_id"] == role_id
    assert data["data"]["is_active"] is False


@pytest.mark.anyio
async def test_delete_user_role_internal_error(mocker, async_client: AsyncClient):
    """Should return 500 on DB exception."""
    mocker.patch("app.services.user_roles_service.database.fetch_one", side_effect=Exception("DB error"))

    response = await delete_user_role_request(async_client, 1)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []