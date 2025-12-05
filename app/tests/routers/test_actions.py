import pytest
from app.db.database import database, IS_SQLITE
from app.db.master.actions import actions_table
from datetime import datetime


# --- Helper functions ---
async def get_all_actions_request():
    """Use global `client` provided by conftest.py"""
    return await client.get("/screens/getallactions")


async def insert_action(name="Test Action", created_by=1, is_active=True):
    values = {
        "action_name": name,
        "created_by": created_by,
        "is_active": is_active,
    }
    if IS_SQLITE:
        values["created_date"] = datetime.utcnow()
    query = actions_table.insert().values(**values)
    return await database.execute(query)


# --- GET Tests ---
@pytest.mark.anyio
async def test_get_all_actions_success():
    """✅ Should fetch all active actions successfully"""
    await insert_action(name="Action A")
    await insert_action(name="Action B")

    response = await get_all_actions_request()
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert "Fetched active actions successfully" in data["message"]
    assert len(data["data"]) >= 2
    assert all("ActionName" in a for a in data["data"])


@pytest.mark.anyio
async def test_get_all_actions_empty():
    """✅ Should return empty list when no actions exist"""
    await database.execute(actions_table.delete())
    response = await get_all_actions_request()
    data = response.json()

    assert response.status_code == 200
    assert isinstance(data["data"], list)


# --- POST Tests ---
@pytest.mark.anyio
async def test_add_action_success():
    """✅ Should add a new action successfully"""
    payload = {"ActionName": "New Action"}
    response = await client.post("/screens/add", json=payload)
    data = response.json()

    assert data["status_code"] == 201
    assert "Action added successfully" in data["message"]
    assert data["data"]["ActionName"] == "New Action"


@pytest.mark.anyio
async def test_add_action_missing_name():
    """⚠️ Currently allows empty ActionName"""
    payload = {"ActionName": ""}
    response = await client.post("/screens/add", json=payload)
    data = response.json()

    # Behavior may change once backend validation is added
    assert data["status_code"] == 201
    assert data["data"]["ActionName"] == ""


# --- PUT Tests ---
@pytest.mark.anyio
async def test_update_action_success():
    """✅ Should update existing action successfully"""
    action_id = await insert_action(name="Old Action")
    payload = {"ActionName": "Updated Action"}

    response = await client.put(f"/screens/update/{action_id}", json=payload)
    data = response.json()

    assert data["status_code"] == 200
    assert "Action updated successfully" in data["message"]
    assert data["data"]["ActionName"] == "Updated Action"


@pytest.mark.anyio
async def test_update_action_not_found():
    """🚫 Should return 404 for non-existent action"""
    payload = {"ActionName": "Nonexistent"}
    response = await client.put("/screens/update/9999", json=payload)
    data = response.json()

    assert data["status_code"] == 404
    assert "Action not found" in data["message"]


# --- DELETE Tests ---
@pytest.mark.anyio
async def test_delete_action_success():
    """✅ Should delete action successfully"""
    action_id = await insert_action(name="To Delete")
    response = await client.delete(f"/screens/delete/{action_id}")
    data = response.json()

    assert data["status_code"] == 200
    assert "Action deleted successfully" in data["message"]
    assert data["data"]["ActionId"] == action_id


@pytest.mark.anyio
async def test_delete_action_not_found():
    """🚫 Should return 404 for deleting non-existent action"""
    response = await client.delete("/screens/delete/9999")
    data = response.json()

    assert data["status_code"] == 404
    assert "Action not found" in data["message"]


@pytest.mark.anyio
async def test_delete_action_internal_server_error(mocker):
    """💥 Should handle DB exceptions gracefully"""
    action_id = await insert_action(name="Error Action")
    mocker.patch(
        "app.services.security.actions_service.database.execute",
        side_effect=Exception("DB error")
    )

    response = await client.delete(f"/screens/delete/{action_id}")
    data = response.json()

    assert data["status_code"] == 500
    assert "Internal server error" in data["message"]
