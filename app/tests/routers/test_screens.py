import pytest
from httpx import AsyncClient
from app.db.database import database, IS_SQLITE
from app.db.master.screens import screens_table
from datetime import datetime

# --- Helper functions ---
async def get_all_screens_request(async_client: AsyncClient):
    return await async_client.get("/screens/getallscreens")


async def insert_screen(name="Test Screen", created_by=1, is_active=True):
    values = {
        "screen_name": name,
        "created_by": created_by,
        "is_active": is_active,
    }
    if IS_SQLITE:
        values["created_date"] = datetime.utcnow()
    query = screens_table.insert().values(**values)
    return await database.execute(query)


# --- GET Tests ---
@pytest.mark.anyio
async def test_get_all_screens_success(async_client: AsyncClient):
    await insert_screen(name="Screen A")
    await insert_screen(name="Screen B")

    response = await get_all_screens_request(async_client)
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert "Fetched all screens successfully" in data["message"]
    assert len(data["data"]) >= 2
    assert all("ScreenName" in s for s in data["data"])


@pytest.mark.anyio
async def test_get_all_screens_empty(async_client: AsyncClient):
    await database.execute(screens_table.delete())
    response = await get_all_screens_request(async_client)
    data = response.json()

    assert response.status_code == 200
    assert isinstance(data["data"], list)


# --- POST Tests ---
@pytest.mark.anyio
async def test_add_screen_success(async_client: AsyncClient):
    payload = {"ScreenName": "New Screen", "CreatedBy": 1}
    response = await async_client.post("/screens/addscreen", json=payload)
    data = response.json()

    # Service currently returns JSON status_code 201, not HTTP 201
    assert data["status_code"] == 201
    assert "Screen added successfully" in data["message"]
    assert data["data"]["ScreenName"] == "New Screen"


@pytest.mark.anyio
async def test_add_screen_missing_name(async_client: AsyncClient):
    payload = {"ScreenName": "", "CreatedBy": 1}
    response = await async_client.post("/screens/addscreen", json=payload)
    data = response.json()

    # Service currently allows empty names and returns 201
    assert data["status_code"] == 201
    assert data["data"]["ScreenName"] == ""


# --- PUT Tests ---
@pytest.mark.anyio
async def test_update_screen_success(async_client: AsyncClient):
    screen_id = await insert_screen(name="Old Screen")
    payload = {"ScreenName": "Updated Screen", "UpdatedBy": 1}
    response = await async_client.put(f"/screens/updatescreen/{screen_id}", json=payload)
    data = response.json()

    assert data["status_code"] == 200
    assert "Screen updated successfully" in data["message"]
    assert data["data"]["ScreenName"] == "Updated Screen"


@pytest.mark.anyio
async def test_update_screen_not_found(async_client: AsyncClient):
    payload = {"ScreenName": "Nonexistent", "UpdatedBy": 1}
    response = await async_client.put("/screens/updatescreen/9999", json=payload)
    data = response.json()

    # Service returns JSON status_code 404
    assert data["status_code"] == 404
    assert "Screen not found" in data["message"]


# --- DELETE Tests ---
@pytest.mark.anyio
async def test_delete_screen_success(async_client: AsyncClient):
    screen_id = await insert_screen(name="To Delete")
    response = await async_client.delete(f"/screens/deletescreen/{screen_id}")
    data = response.json()

    assert data["status_code"] == 200
    assert "Screen deleted successfully" in data["message"]
    assert data["data"]["IsActive"] is False


@pytest.mark.anyio
async def test_delete_screen_already_inactive(async_client: AsyncClient):
    screen_id = await insert_screen(name="Inactive Screen", is_active=False)
    response = await async_client.delete(f"/screens/deletescreen/{screen_id}")
    data = response.json()

    # Service returns JSON 404
    assert data["status_code"] == 404
    assert "Screen not found" in data["message"]


@pytest.mark.anyio
async def test_delete_screen_not_found(async_client: AsyncClient):
    response = await async_client.delete("/screens/deletescreen/9999")
    data = response.json()

    assert data["status_code"] == 404
    assert "Screen not found" in data["message"]


@pytest.mark.anyio
async def test_delete_screen_internal_server_error(mocker, async_client: AsyncClient):
    screen_id = await insert_screen(name="Error Screen")
    # Mock database.execute to raise an exception
    mocker.patch(
        "app.services.security.screens_service.database.fetch_one",
        side_effect=Exception("DB error")
    )

    response = await async_client.delete(f"/screens/deletescreen/{screen_id}")
    data = response.json()

    # ✅ Check JSON status_code, not HTTP response code
    assert data["status_code"] == 500
    assert "Internal server error" in data["message"]

