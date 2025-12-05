import pytest
from httpx import AsyncClient
from fastapi import status


# --- GET: get_task_work_log_details_by_project_task_id (Success) ---
@pytest.mark.anyio
async def test_get_task_work_log_details_success(mocker, async_client: AsyncClient):
    mock_result = ('{"status_code": 200, "message": "Success", "data": [{"log_id": 1}]}' ,)
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", return_value=mock_result)

    resp = await async_client.get("/transaction/getTaskWorkLogDetailsByProjectTaskId", params={"project_task_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status_code"] == 200


# --- GET: get_task_work_log_details_by_project_task_id (Null/Unexpected Response) ---
@pytest.mark.anyio
async def test_get_task_work_log_details_null_response(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", return_value=(None,))
    resp = await async_client.get("/transaction/getTaskWorkLogDetailsByProjectTaskId", params={"project_task_id": 2})
    assert resp.status_code == 500


# --- GET: get_task_work_log_details_by_project_task_id (Exception) ---
@pytest.mark.anyio
async def test_get_task_work_log_details_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", side_effect=Exception("DB failure"))
    resp = await async_client.get("/transaction/getTaskWorkLogDetailsByProjectTaskId", params={"project_task_id": 3})
    assert resp.status_code == 500


# --- POST: create_task_work_log (Success) ---
@pytest.mark.anyio
async def test_create_task_work_log_success(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", side_effect=[
        {"project_task_id": 1},  # Project task exists
        {"user_id": 10}          # User exists
    ])
    mocker.patch("app.services.transaction.task_work_log_service.database.execute", return_value=99)

    payload = {"project_task_id": 1, "user_id": 10, "remarks": "Initial log"}
    resp = await async_client.post("/transaction/createTaskWorkLog", json=payload)

    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["message"] == "Task work log created successfully"


# --- POST: create_task_work_log (Invalid project_task_id) ---
@pytest.mark.anyio
async def test_create_task_work_log_invalid_project_id(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", return_value=None)
    payload = {"project_task_id": 999, "user_id": 1, "remarks": "Invalid project"}
    resp = await async_client.post("/transaction/createTaskWorkLog", json=payload)
    assert resp.status_code == 404
    assert "Invalid project_task_id" in resp.text


# --- POST: create_task_work_log (Invalid user_id) ---
@pytest.mark.anyio
async def test_create_task_work_log_invalid_user(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", side_effect=[
        {"project_task_id": 1},  # Project task exists
        None                     # User not found
    ])
    payload = {"project_task_id": 1, "user_id": 99, "remarks": "Invalid user"}
    resp = await async_client.post("/transaction/createTaskWorkLog", json=payload)
    assert resp.status_code == 404
    assert "Invalid user_id" in resp.text


# --- POST: create_task_work_log (Exception) ---
@pytest.mark.anyio
async def test_create_task_work_log_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", side_effect=Exception("Simulated DB Error"))
    payload = {"project_task_id": 1, "user_id": 1, "remarks": "Test"}
    resp = await async_client.post("/transaction/createTaskWorkLog", json=payload)
    assert resp.status_code == 500


# --- POST: update_project_task_status (Success) ---
@pytest.mark.anyio
async def test_update_project_task_status_success(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", return_value={"project_task_id": 1})
    mocker.patch("app.services.transaction.task_work_log_service.database.execute", return_value=True)

    payload = {"project_task_id": 1, "task_status_id": 2}
    resp = await async_client.post("/transaction/updateProjectTaskStatusForTaskWorkLog", json=payload)
    assert resp.status_code == 200
    assert "Task status updated successfully" in resp.text


# --- POST: update_project_task_status (Missing fields) ---
@pytest.mark.anyio
async def test_update_project_task_status_missing_fields(async_client: AsyncClient):
    payload = {"project_task_id": None, "task_status_id": None}
    resp = await async_client.post("/transaction/updateProjectTaskStatusForTaskWorkLog", json=payload)
    assert resp.status_code in [400, 422]


# --- POST: update_project_task_status (Project task not found) ---
@pytest.mark.anyio
async def test_update_project_task_status_not_found(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", return_value=None)
    payload = {"project_task_id": 5, "task_status_id": 10}
    resp = await async_client.post("/transaction/updateProjectTaskStatusForTaskWorkLog", json=payload)
    assert resp.status_code == 404
    assert "Project task not found" in resp.text


# --- POST: update_project_task_status (Exception) ---
@pytest.mark.anyio
async def test_update_project_task_status_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.task_work_log_service.database.fetch_one", side_effect=Exception("Update failed"))
    payload = {"project_task_id": 10, "task_status_id": 20}
    resp = await async_client.post("/transaction/updateProjectTaskStatusForTaskWorkLog", json=payload)
    assert resp.status_code == 500
