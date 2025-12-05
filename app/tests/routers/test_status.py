import pytest
from httpx import AsyncClient

from app.db.database import database
from app.db.master.status import status_table


@pytest.mark.anyio
async def test_create_status_success(async_client: AsyncClient):
    payload = {"status_name": "In Progress"}

    response = await async_client.post("/master/createStatus", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status_code"] == 201
    assert data["message"] == "Status created successfully"
    assert data["data"]["status_name"] == "In Progress"


@pytest.mark.anyio
async def test_create_status_conflict_existing(async_client: AsyncClient):
    # Create once
    payload = {"status_name": "Completed"}
    await async_client.post("/master/createStatus", json=payload)

    # Create again with same name
    response = await async_client.post("/master/createStatus", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]


@pytest.mark.anyio
async def test_get_all_status_with_data(async_client):
    # Insert dummy status into the test database
    query = status_table.insert().values(status_name="Active", is_active=True)
    await database.execute(query)

    # Call the API
    response = await async_client.get("/master/getAllStatus")

    assert response.status_code == 200
    json_data = response.json()

    assert json_data["status_code"] == 200
    assert json_data["message"] == "status fetched successfully"
    assert len(json_data["data"]) > 0
    assert json_data["data"][0]["status_name"] == "Active"


@pytest.mark.anyio
async def test_update_status_success(async_client: AsyncClient):
    # Insert a fresh status
    payload = {"status_name": "Review Pending"}
    create_res = await async_client.post("/master/createStatus", json=payload)
    status_id = create_res.json()["data"]["status_id"]

    update_payload = {"status_id": status_id, "status_name": "Review Completed"}
    response = await async_client.put("/master/updateStatus", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "status updated successfully"
    assert data["data"]["status_name"] == "Review Completed"


@pytest.mark.anyio
async def test_update_status_conflict(async_client: AsyncClient):
    # Create 2 statuses
    await async_client.post("/master/createStatus", json={"status_name": "QA"})
    res2 = await async_client.post("/master/createStatus", json={"status_name": "Dev"})

    status_id_2 = res2.json()["data"]["status_id"]

    # Try updating 2nd to 1st’s name
    update_payload = {"status_id": status_id_2, "status_name": "QA"}
    response = await async_client.put("/master/updateStatus", json=update_payload)

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]


@pytest.mark.anyio
async def test_delete_status_success(async_client: AsyncClient):
    # Create a status
    create_res = await async_client.post("/master/createStatus", json={"status_name": "To be deleted"})
    status_id = create_res.json()["data"]["status_id"]

    delete_payload = {"status_id": status_id}
    response = await async_client.request("DELETE", "/master/deleteStatus", json=delete_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "status inactivated successfully"
    assert data["data"]["is_active"] is False


@pytest.mark.anyio
async def test_delete_status_already_inactive(async_client: AsyncClient):
    # Create and delete
    create_res = await async_client.post("/master/createStatus", json={"status_name": "Already Inactive"})
    status_id = create_res.json()["data"]["status_id"]
    await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": status_id})

    # Try deleting again
    response = await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": status_id})

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["message"] == "status is already inactive"


@pytest.mark.anyio
async def test_create_status_missing_name(async_client: AsyncClient):
    response = await async_client.post("/master/createStatus", json={"status_name": ""})
    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "status name is required"

@pytest.mark.anyio
async def test_create_status_reactivates_inactive(async_client: AsyncClient):
    # Create
    res = await async_client.post("/master/createStatus", json={"status_name": "Dormant"})
    status_id = res.json()["data"]["status_id"]

    # Delete → make inactive
    await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": status_id})

    # Create again with same name
    response = await async_client.post("/master/createStatus", json={"status_name": "Dormant"})
    assert response.status_code == 200
    data = response.json()
    assert "activated successfully" in data["message"]

@pytest.mark.anyio
async def test_get_all_status_none_found(mocker, async_client: AsyncClient):
    mocker.patch("app.services.status_service.database.fetch_all", return_value=[])
    response = await async_client.get("/master/getAllStatus")
    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "No status found"

@pytest.mark.anyio
async def test_update_status_missing_id(async_client: AsyncClient):
    payload = {"status_name": "Something"}
    response = await async_client.put("/master/updateStatus", json=payload)

    assert response.status_code == 400  # changed from 400



@pytest.mark.anyio
async def test_update_status_missing_name(async_client: AsyncClient):
    # Create first
    res = await async_client.post("/master/createStatus", json={"status_name": "Temp"})
    status_id = res.json()["data"]["status_id"]

    # Update with empty name
    response = await async_client.put("/master/updateStatus", json={"status_id": status_id, "status_name": ""})
    assert response.status_code == 400
    assert response.json()["message"] == "status name is required"

@pytest.mark.anyio
async def test_update_status_not_found(async_client: AsyncClient):
    response = await async_client.put("/master/updateStatus", json={"status_id": 9999, "status_name": "Ghost"})
    assert response.status_code == 404
    assert response.json()["message"] == "status not found"

@pytest.mark.anyio
async def test_delete_status_missing_id(async_client: AsyncClient):
    response = await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": None})
    assert response.status_code == 400
    assert response.json()["message"] == "status ID is required"

@pytest.mark.anyio
async def test_delete_status_not_found(async_client: AsyncClient):
    response = await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": 9999})
    assert response.status_code == 404
    assert response.json()["message"] == "status not found"

@pytest.mark.anyio
async def test_get_all_status_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.status_service.database.fetch_all", side_effect=Exception("DB error"))
    response = await async_client.get("/master/getAllStatus")
    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"

@pytest.mark.anyio
async def test_create_status_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.status_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await async_client.post("/master/createStatus", json={"status_name": "FailTest"})
    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"

@pytest.mark.anyio
async def test_update_status_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.status_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await async_client.put("/master/updateStatus", json={"status_id": 1, "status_name": "Broken"})
    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"

@pytest.mark.anyio
async def test_delete_status_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.status_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await async_client.request("DELETE", "/master/deleteStatus", json={"status_id": 1})
    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"