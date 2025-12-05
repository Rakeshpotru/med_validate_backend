import pytest
from httpx import AsyncClient
from app.main import app
from app.db.master.work_flow_stages import work_flow_stages_table
from app.db.master.work_flow_stage_phase_mapping import work_flow_stage_phase_mapping_table
from app.db.database import database

@pytest.mark.asyncio
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def setup_teardown():
    await database.connect()

    # seed stages
    await database.execute_many(
        query=work_flow_stages_table.insert(),
        values=[
            {"work_flow_stage_id": 1, "work_flow_stage_name": "Initial", "is_active": True},
            {"work_flow_stage_id": 2, "work_flow_stage_name": "Planning", "is_active": True},
        ],
    )

    # seed phases mapping
    await database.execute_many(
        query=work_flow_stage_phase_mapping_table.insert(),
        values=[
            {"stage_id": 1, "phase_id": 2},
            {"stage_id": 1, "phase_id": 3},
        ],
    )

    yield
    await database.disconnect()


@pytest.mark.asyncio
async def test_get_all_workflow_stages():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/workflow-stages")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 2
    assert data[0]["work_flow_stage_name"] == "Initial"


@pytest.mark.asyncio
async def test_get_stage_phase_mappings():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/stage-phase-mappings")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["stage_id"] == 1
    assert len(data[0]["phases"]) == 2


@pytest.mark.asyncio
async def test_map_phases_success():
    payload = {
        "stage_id": 2,
        "phase_ids": [4, 5]
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/workflow-stage-phase-mapping", json=payload)

    assert response.status_code == 200
    assert response.json()["message"] == "Mapping updated"


@pytest.mark.asyncio
async def test_map_phases_without_stage_id():
    payload = {
        "phase_ids": [4]
    }

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/workflow-stage-phase-mapping", json=payload)

    assert response.status_code == 422  # validation error


@pytest.mark.asyncio
async def test_map_phases_empty_phase_ids():
    payload = {"stage_id": 1, "phase_ids": []}

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/workflow-stage-phase-mapping", json=payload)

    # expected -> backend should reject
    assert response.status_code in [400,422]


@pytest.mark.asyncio
async def test_delete_mapping_success():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete("/workflow-stage-phase-mapping/1/2")

    assert response.status_code == 200
    assert response.json()["message"] == "Mapping removed"


@pytest.mark.asyncio
async def test_delete_mapping_not_exists():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete("/workflow-stage-phase-mapping/99/88")

    assert response.status_code in [404,200]
