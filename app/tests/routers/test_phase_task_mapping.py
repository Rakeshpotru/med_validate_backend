import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.sdlc_tasks import sdlc_tasks_table

# --- Helper functions ---
async def insert_phase(name="Phase X", is_active=True):
    query = sdlc_phases_table.insert().values(phase_name=name, is_active=is_active)
    return await database.execute(query)

async def insert_task(name="Task X", is_active=True):
    query = sdlc_tasks_table.insert().values(task_name=name, is_active=is_active)
    return await database.execute(query)

async def insert_phase_task_mapping(phase_id, task_id, is_active=True):
    query = sdlc_phase_tasks_mapping_table.insert().values(
        phase_id=phase_id, task_id=task_id, is_active=is_active
    )
    return await database.execute(query)

# =========================================================
# GET /master/getSDLCPhasesWithTasks
# =========================================================
@pytest.mark.anyio
async def test_get_sdlc_phases_with_tasks_success(async_client: AsyncClient):
    phase_id = await insert_phase("Phase A")
    task1_id = await insert_task("Task 1")
    task2_id = await insert_task("Task 2")
    await insert_phase_task_mapping(phase_id, task1_id)
    await insert_phase_task_mapping(phase_id, task2_id)

    response = await async_client.get("/master/getSDLCPhasesWithTasks")

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    # 👇 fix here
    assert data["message"] == "SDLC phases with tasks fetched successfully"
    assert len(data["data"]) >= 1
    assert any(phase["phase_name"] == "Phase A" for phase in data["data"])
    assert any(task["task_name"] == "Task 1" for phase in data["data"] for task in phase["tasks"])


@pytest.mark.anyio
async def test_get_sdlc_phases_with_tasks_empty(async_client: AsyncClient):
    response = await async_client.get("/master/getSDLCPhasesWithTasks")

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No active phase-task mappings found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_sdlc_phases_with_tasks_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.phase_task_mapping_service.database.fetch_all", side_effect=Exception("DB error"))

    response = await async_client.get("/master/getSDLCPhasesWithTasks")

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# =========================================================
# POST /master/mapPhaseToTasks
# =========================================================
@pytest.mark.anyio
async def test_map_phase_to_tasks_success_insert_and_activate(async_client: AsyncClient):
    phase_id = await insert_phase("Phase B")
    task1_id = await insert_task("Task X")
    task2_id = await insert_task("Task Y")

    payload = {"phase_id": phase_id, "task_ids": [task1_id, task2_id]}
    response = await async_client.post("/master/mapPhaseToTasks", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Phase to task mapping updated successfully"


@pytest.mark.anyio
async def test_map_phase_to_tasks_invalid_phase_id(async_client: AsyncClient):
    """ Should fail when phase_id is invalid."""
    payload = {"phase_id": 0, "task_ids": [1]}
    response = await async_client.post("/master/mapPhaseToTasks", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "status_code" not in data  # API doesn’t include it
    assert data["message"] == "Valid phase_id is required"
    assert data["data"] == []



@pytest.mark.anyio
async def test_map_phase_to_tasks_invalid_task_ids(async_client: AsyncClient):
    """❌ Should fail when task_ids list is invalid or empty."""
    phase_id = await insert_phase("Phase C")
    payload = {"phase_id": phase_id, "task_ids": []}
    response = await async_client.post("/master/mapPhaseToTasks", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert "status_code" not in data
    assert data["message"] == "Valid task_ids list is required"
    assert data["data"] == []


@pytest.mark.anyio
async def test_map_phase_to_tasks_deactivate(async_client: AsyncClient):
    phase_id = await insert_phase("Phase D")
    task1_id = await insert_task("Task Active")
    task2_id = await insert_task("Task Remove")

    # Active mappings
    await insert_phase_task_mapping(phase_id, task1_id, is_active=True)
    await insert_phase_task_mapping(phase_id, task2_id, is_active=True)

    # Keep only task1_id active
    payload = {"phase_id": phase_id, "task_ids": [task1_id]}
    response = await async_client.post("/master/mapPhaseToTasks", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Phase to task mapping updated successfully"


@pytest.mark.anyio
async def test_map_phase_to_tasks_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.phase_task_mapping_service.database.fetch_all", side_effect=Exception("DB fail"))

    payload = {"phase_id": 1, "task_ids": [1]}
    response = await async_client.post("/master/mapPhaseToTasks", json=payload)

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []
