import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.master.risk_sdlcphase_mapping import risk_sdlcphase_mapping_table
from app.db.master.equipment_ai_docs import equipment_ai_docs_table

# ----------------------
# Helper functions
# ----------------------

async def get_all_phases_request(async_client: AsyncClient):
    return await async_client.get("/master/getAllPhases")

async def create_phase_request(async_client: AsyncClient, phase_name: str, order_id: int = 1, is_active: bool = True):
    payload = {"phase_name": phase_name, "order_id": order_id, "is_active": is_active}
    return await async_client.post("/master/createPhase", json=payload)

async def update_phase_request(async_client: AsyncClient, phase_id: int, phase_name: str, order_id: int = 1):
    payload = {"phase_id": phase_id, "phase_name": phase_name, "order_id": order_id}
    return await async_client.put("/master/updatePhase", json=payload)

async def delete_phase_request(async_client: AsyncClient, phase_id: int):
    payload = {"phase_id": phase_id}
    return await async_client.request("DELETE", "/master/deletePhase", json=payload)

async def insert_phase(phase_name: str, order_id: int = 1, is_active: bool = True):
    query = sdlc_phases_table.insert().values(phase_name=phase_name, order_id=order_id, is_active=is_active)
    return await database.execute(query)

# ----------------------
# Tests for getAllPhases
# ----------------------

@pytest.mark.anyio
async def test_get_all_phases_success(async_client: AsyncClient):
    await insert_phase("Requirements", order_id=1)
    await insert_phase("Design", order_id=2)
    response = await get_all_phases_request(async_client)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "phases fetched successfully"
    assert len(data["data"]) == 2

@pytest.mark.anyio
async def test_get_all_phases_empty(async_client: AsyncClient):
    response = await get_all_phases_request(async_client)
    assert response.status_code == 404
    data = response.json()
    assert data["data"] == []

@pytest.mark.anyio
async def test_get_all_phases_only_inactive(async_client: AsyncClient):
    await insert_phase("Deployment", order_id=1, is_active=False)
    response = await get_all_phases_request(async_client)
    assert response.status_code == 404
    data = response.json()
    assert data["data"] == []

# ----------------------
# Tests for createPhase
# ----------------------

@pytest.mark.anyio
async def test_create_phase_success(async_client: AsyncClient):
    response = await create_phase_request(async_client, "Analysis", order_id=1)
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["phase_name"] == "Analysis"

@pytest.mark.anyio
async def test_create_phase_missing_name(async_client: AsyncClient):
    response = await create_phase_request(async_client, "", order_id=1)
    assert response.status_code == 400

@pytest.mark.anyio
async def test_create_phase_conflict(async_client: AsyncClient):
    await insert_phase("Existing Phase", order_id=1)
    response = await create_phase_request(async_client, "Existing Phase", order_id=2)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_create_phase_activate_inactive(async_client: AsyncClient):
    phase_id = await insert_phase("Inactive Phase", order_id=1, is_active=False)
    response = await create_phase_request(async_client, "Inactive Phase", order_id=1)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["phase_id"] == phase_id

# ----------------------
# Tests for updatePhase
# ----------------------

@pytest.mark.anyio
async def test_update_phase_missing_name(async_client: AsyncClient):
    phase_id = await insert_phase("Old Phase", order_id=1)
    response = await update_phase_request(async_client, phase_id, "", order_id=1)
    assert response.status_code == 400

@pytest.mark.anyio
async def test_update_phase_not_found(async_client: AsyncClient):
    response = await update_phase_request(async_client, 9999, "Nonexistent", order_id=1)
    assert response.status_code == 404

@pytest.mark.anyio
async def test_update_phase_conflict(async_client: AsyncClient):
    id1 = await insert_phase("Phase A", order_id=1)
    id2 = await insert_phase("Phase B", order_id=2)
    response = await update_phase_request(async_client, id2, "Phase A", order_id=2)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_update_phase_success(async_client: AsyncClient):
    phase_id = await insert_phase("Old Phase", order_id=1)
    response = await update_phase_request(async_client, phase_id, "Updated Phase", order_id=2)
    assert response.status_code == 200

# ----------------------
# Tests for deletePhase
# ----------------------

@pytest.mark.anyio
async def test_delete_phase_mapped_to_task(async_client: AsyncClient):
    phase_id = await insert_phase("Mapped Phase", order_id=1)
    await database.execute(sdlc_phase_tasks_mapping_table.insert().values(phase_id=phase_id, task_id=1, is_active=True))
    response = await delete_phase_request(async_client, phase_id)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_delete_phase_mapped_to_risk(async_client: AsyncClient):
    phase_id = await insert_phase("Risk Phase", order_id=1)
    await database.execute(risk_sdlcphase_mapping_table.insert().values(phase_id=phase_id, risk_assessment_id=1, is_active=True))
    response = await delete_phase_request(async_client, phase_id)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_delete_phase_mapped_to_equipment(async_client: AsyncClient):
    phase_id = await insert_phase("Equipment Phase", order_id=1)
    await database.execute(equipment_ai_docs_table.insert().values(phase_id=phase_id, document_json="dummy"))
    response = await delete_phase_request(async_client, phase_id)
    assert response.status_code == 409

@pytest.mark.anyio
async def test_delete_phase_success(async_client: AsyncClient):
    phase_id = await insert_phase("Active Phase", order_id=1)
    response = await delete_phase_request(async_client, phase_id)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["is_active"] is False
