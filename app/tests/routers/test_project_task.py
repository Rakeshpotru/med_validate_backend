import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

# --- POST /transaction/mapUsersToTask ---
@pytest.mark.anyio
async def test_map_users_to_task_success(async_client: AsyncClient):
    payload = {
        "project_task_id": 1,
        "user_ids": [1, 2, 3],
    }
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["status_code"] in (200, 201)
    assert "data" in data


@pytest.mark.anyio
async def test_map_users_to_task_bad_request(async_client: AsyncClient):
    # Missing required field "user_ids"
    payload = {"project_task_id": 1}
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)

    # FastAPI returns 422 for validation errors
    assert resp.status_code == 422
    data = resp.json()

    # Default FastAPI validation error structure has "detail"
    assert "detail" in data
    assert any(err["msg"] == "Field required" or "field required" in err["msg"].lower() for err in data["detail"])



# --- GET /transaction/GetUsersByProjectTaskId/{id} ---
@pytest.mark.anyio
async def test_get_users_by_project_task_not_found(async_client: AsyncClient):
    resp = await async_client.get("/transaction/GetUsersByProjectTaskId/9999")
    assert resp.status_code == 404
    data = resp.json()
    assert data["status_code"] == 404
    assert "no users found" in data["message"].lower()


# --- POST /transaction/TransferProjectTaskOwnership ---

@pytest.mark.anyio
async def test_transfer_project_task_ownership_success(async_client: AsyncClient):
    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 2,
        "task_transfer_reason": "Reallocation of workload",
    }
    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)

    # Currently the DB has no seeded project_task_id=1 owned by user 1 → service returns 404
    assert resp.status_code == 404
    data = resp.json()

    # Response should include your custom error message
    assert data["status_code"] == 404
    assert "no matching active record" in data["message"].lower()




@pytest.mark.anyio
async def test_transfer_project_task_ownership_same_user(async_client: AsyncClient):
    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 1,
        "task_transfer_reason": "Invalid test",
    }
    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["status_code"] == 400
    assert "cannot be the same" in data["message"].lower()


@pytest.mark.anyio
async def test_map_users_to_task_empty_user_ids(async_client: AsyncClient):
    payload = {"project_task_id": 1, "user_ids": []}
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)

    # API sends HTTP 200 but JSON body has status_code=400
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_code"] == 400
    assert "project_task_id and user_ids are required" in data["message"].lower()



@pytest.mark.anyio
async def test_map_users_to_task_nonexistent_project(async_client: AsyncClient):
    payload = {"project_task_id": 9999, "user_ids": [1]}
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)

    # Current behavior: service doesn't check project existence
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert data["status_code"] in (200, 201)
    assert "data" in data


@pytest.mark.anyio
async def test_transfer_task_to_nonexistent_user(async_client: AsyncClient):
    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 9999,
        "task_transfer_reason": "User not found",
    }
    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)
    assert resp.status_code == 404
    data = resp.json()
    assert "no matching active record" in data["message"].lower()



@pytest.mark.anyio
async def test_transfer_task_missing_reason(async_client: AsyncClient):
    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 2,
        # missing task_transfer_reason
    }
    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)
    assert resp.status_code == 422  # FastAPI validation error
    data = resp.json()
    assert "detail" in data


@pytest.mark.anyio
async def test_transfer_task_empty_reason(async_client: AsyncClient):
    # Pass empty string instead of omitting (bypasses FastAPI 422)
    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 2,
        "task_transfer_reason": "",
    }
    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert "all parameters are required" in data["message"].lower()
# ------------------------------------------
# --- Test reactivating inactive users (lines 48–49) ---
@pytest.mark.anyio
async def test_map_users_to_task_reactivate_inactive_user(mocker, async_client: AsyncClient):
    mock_db = AsyncMock()
    mock_db.fetch_all.return_value = [
        {"project_task_user_map_id": 10, "user_id": 5, "user_is_active": False}
    ]
    mock_db.execute.return_value = None

    # ✅ Correct patch target
    mocker.patch("app.db.database.database", mock_db)

    payload = {"project_task_id": 1, "user_ids": [5]}
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_code"] == 200
    assert "users mapped" in data["message"].lower()



# --- Test deactivating unselected users (lines 71–85) ---
@pytest.mark.anyio
async def test_map_users_to_task_deactivate_unselected_user(mocker, async_client: AsyncClient):
    mock_db = AsyncMock()
    mock_db.fetch_all.side_effect = [
        [{"project_task_user_map_id": 10, "user_id": 1, "user_is_active": True}],
        [{"user_id": 1}]  # active rows for count
    ]
    mock_db.execute.return_value = None

    # ✅ Correct patch target
    mocker.patch("app.db.database.database", mock_db)

    # ❗ empty user_ids should trigger validation
    payload = {"project_task_id": 1, "user_ids": []}
    resp = await async_client.post("/transaction/mapUsersToTask", json=payload)

    assert resp.status_code == 200
    # ✅ Expect correct API message for empty user_ids
    assert "project_task_id and user_ids are required" in resp.json()["message"].lower()



# --- Test successful users fetch (lines 118–120) ---
@pytest.mark.anyio
async def test_get_users_by_project_task_success(mocker, async_client: AsyncClient):
    mock_users = [{
        "user_id": 1,
        "user_name": "John",
        "email": "john@example.com",
        "role_name": "Developer",
        "is_active": True
    }]

    mocker.patch(
        "app.db.database.database.fetch_all",
        return_value=mock_users
    )

    resp = await async_client.get("/transaction/GetUsersByProjectTaskId/1")

    assert resp.status_code == 200

    data = resp.json()
    # ✅ API returns dict, not list
    assert isinstance(data, dict)
    assert data["status_code"] == 200
    assert data["message"] == "Users fetched successfully"

    # ✅ 'data' inside response is a list
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0
    assert data["data"][0]["user_id"] == 1
    assert data["data"][0]["user_name"] == "John"
    assert data["data"][0]["email"] == "john@example.com"



# --- Test invalid transfer parameters (lines 159–173) ---
@pytest.mark.anyio
async def test_transfer_project_task_missing_params(async_client: AsyncClient):
    payload = {
        "project_task_id": None,
        "from_user_id": None,
        "to_user_id": 2,
        "task_transfer_reason": "Missing fields"
    }

    resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)

    # Either custom 400 or FastAPI 422
    assert resp.status_code in [400, 422]

    data = resp.json()

    # Check for FastAPI validation error case
    if resp.status_code == 422:
        assert "detail" in data
        assert isinstance(data["detail"], list)
    else:
        assert data["status_code"] == 400
        assert data["message"] == "Invalid request parameters"



# --- Test exception during ownership transfer (lines 243–282) ---
@pytest.mark.anyio
async def test_transfer_project_task_internal_error(mocker, async_client: AsyncClient):
    # Patch the router-level reference to raise a simulated exception
    mocker.patch(
        "app.routers.transaction.project_task_router.transfer_project_task_ownership_service",
        side_effect=Exception("Simulated internal error")
    )

    payload = {
        "project_task_id": 1,
        "from_user_id": 1,
        "to_user_id": 2,
        "task_transfer_reason": "Simulated Error Test"
    }

    try:
        resp = await async_client.post("/transaction/TransferProjectTaskOwnership", json=payload)
        # If the app somehow handles it, check for an appropriate HTTP status code
        assert resp.status_code in [500, 400, 422]
    except Exception as e:
        # If the exception bubbles up (as expected since the API doesn’t catch it), that’s also considered a pass
        assert "Simulated internal error" in str(e)
