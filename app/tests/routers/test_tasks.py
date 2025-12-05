import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table


# --- Helper functions ---
async def get_all_tasks_request(async_client: AsyncClient):
    """Send GET request to fetch all tasks."""
    return await async_client.get("/master/getAllTasks")

async def create_task_request(async_client: AsyncClient, task_name: str, order_id: int = 1, is_active: bool = True):
    """Send POST request to create a task."""
    payload = {"task_name": task_name, "order_id": order_id, "is_active": is_active}
    return await async_client.post("/master/createTask", json=payload)


async def update_task_request(async_client: AsyncClient, task_id: int, task_name: str, order_id: int = 1):
    """Send PUT request to update a task."""
    payload = {"task_id": task_id, "task_name": task_name, "order_id": order_id}
    return await async_client.put("/master/updateTask", json=payload)



async def delete_task_request(async_client: AsyncClient, task_id: int):
    """Send DELETE request to delete a task."""
    payload = {"task_id": task_id}
    return await async_client.request("DELETE", "/master/deleteTask", json=payload)


async def insert_task(task_name: str, order_id: int = 1, is_active: bool = True):
    query = sdlc_tasks_table.insert().values(task_name=task_name, order_id=order_id, is_active=is_active)
    return await database.execute(query)


# --- Test cases for getAllTasks ---
@pytest.mark.anyio
async def test_get_all_tasks_success(async_client: AsyncClient):
    await insert_task("Development", order_id=1)
    await insert_task("Testing", order_id=2)

    response = await get_all_tasks_request(async_client)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "tasks fetched successfully"
    assert len(data["data"]) == 2
    assert all("task_name" in task for task in data["data"])

@pytest.mark.anyio
async def test_get_all_tasks_empty(async_client: AsyncClient):
    response = await get_all_tasks_request(async_client)

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No tasks found"
    assert data["data"] == []

@pytest.mark.anyio
async def test_get_all_tasks_only_inactive(async_client: AsyncClient):
    await insert_task("Deployment", order_id=1, is_active=False)
    response = await get_all_tasks_request(async_client)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No tasks found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_tasks_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.task_service.database.fetch_all", side_effect=Exception("DB error"))
    response = await get_all_tasks_request(async_client)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# --- Test cases for createTask ---
@pytest.mark.anyio
async def test_create_task_success(async_client: AsyncClient):
    response = await create_task_request(async_client, "New Task", order_id=1)
    assert response.status_code == 201
    data = response.json()
    assert data["status_code"] == 201
    assert data["message"] == "task created successfully"
    assert data["data"]["task_name"] == "New Task"
    assert "task_id" in data["data"]


@pytest.mark.anyio
async def test_create_task_missing_name(async_client: AsyncClient):
    response = await create_task_request(async_client, "", order_id=1)
    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "task name is required"
    assert data["data"] == []


@pytest.mark.anyio
async def test_create_task_conflict(async_client: AsyncClient):
    await insert_task("Existing Task", order_id=1, is_active=True)
    response = await create_task_request(async_client, "Existing Task", order_id=2)
    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]
    assert data["data"] == []


@pytest.mark.anyio
async def test_create_task_activate_inactive(async_client: AsyncClient):
    task_id = await insert_task("Inactive Task", order_id=1, is_active=False)
    response = await create_task_request(async_client, "Inactive Task", order_id=1)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert "activated successfully" in data["message"]
    assert data["data"]["task_id"] == task_id
    assert data["data"]["task_name"] == "Inactive Task"


@pytest.mark.anyio
async def test_create_task_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.task_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await create_task_request(async_client, "ErrorTask", order_id=1)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# --- Test cases for updateTask ---
@pytest.mark.anyio
async def test_update_task_missing_name(async_client: AsyncClient):
    task_id = await insert_task("Old Task", order_id=1)
    response = await update_task_request(async_client, task_id, "", order_id=1)
    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "task name is required"
    assert data["data"] == []


@pytest.mark.anyio
async def test_update_task_not_found(async_client: AsyncClient):
    response = await update_task_request(async_client, 9999, "Nonexistent", order_id=1)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "task not found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_update_task_conflict(async_client: AsyncClient):
    task1_id = await insert_task("Existing Task", order_id=1, is_active=True)
    task2_id = await insert_task("Another Task", order_id=2, is_active=True)
    response = await update_task_request(async_client, task2_id, "Existing Task", order_id=2)
    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]
    assert data["data"] == []


@pytest.mark.anyio
async def test_update_task_success(async_client: AsyncClient):
    task_id = await insert_task("Old Task", order_id=1)
    response = await update_task_request(async_client, task_id, "Updated Task", order_id=1)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "task updated successfully"
    assert data["data"]["task_id"] == task_id
    assert data["data"]["task_name"] == "Updated Task"


@pytest.mark.anyio
async def test_update_task_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.task_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await update_task_request(async_client, 1, "Broken", order_id=1)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# --- Test cases for deleteTask ---
@pytest.mark.anyio
async def test_delete_task_not_found(async_client: AsyncClient):
    response = await delete_task_request(async_client, 9999)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "task not found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_delete_task_already_inactive(async_client: AsyncClient):
    task_id = await insert_task("Inactive Task", order_id=1, is_active=False)
    response = await delete_task_request(async_client, task_id)
    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["message"] == "task is already inactive"
    assert data["data"] == []


@pytest.mark.anyio
async def test_delete_task_mapped_to_phase(async_client: AsyncClient):
    task_id = await insert_task("Mapped Task", order_id=1)
    await database.execute(sdlc_phase_tasks_mapping_table.insert().values(task_id=task_id, phase_id=1))
    response = await delete_task_request(async_client, task_id)
    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["message"] == "Task is mapped to a phase and cannot be inactivated"
    assert data["data"] == []


@pytest.mark.anyio
async def test_delete_task_success(async_client: AsyncClient):
    task_id = await insert_task("Active Task", order_id=1, is_active=True)
    response = await delete_task_request(async_client, task_id)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "task inactivated successfully"
    assert data["data"]["task_id"] == task_id
    assert data["data"]["is_active"] is False


@pytest.mark.anyio
async def test_delete_task_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.task_service.database.fetch_one", side_effect=Exception("DB error"))
    response = await delete_task_request(async_client, 1)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []
