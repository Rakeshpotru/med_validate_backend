import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.risk_assessment import risk_assessment_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.risk_sdlcphase_mapping import risk_sdlcphase_mapping_table

# ------------------------------
# Helpers
# ------------------------------
async def insert_risk(name="Risk X", is_active=True):
    query = risk_assessment_table.insert().values(
        risk_assessment_name=name,
        is_active=is_active
    )
    return await database.execute(query)

async def insert_phase(name="Phase X", is_active=True):
    query = sdlc_phases_table.insert().values(
        phase_name=name,
        is_active=is_active
    )
    return await database.execute(query)

async def insert_risk_phase_mapping(risk_id, phase_id, is_active=True):
    query = risk_sdlcphase_mapping_table.insert().values(
        risk_assessment_id=risk_id,
        phase_id=phase_id,
        is_active=is_active
    )
    return await database.execute(query)

# ========================================================
# GET /master/getAllMappedRisksWithPhases
# ========================================================
@pytest.mark.anyio
async def test_get_all_mapped_risks_with_phases_success(async_client: AsyncClient):
    risk_id = await insert_risk("Risk A")
    phase1 = await insert_phase("Phase 1")
    phase2 = await insert_phase("Phase 2")

    await insert_risk_phase_mapping(risk_id, phase1)
    await insert_risk_phase_mapping(risk_id, phase2)

    response = await async_client.get("/master/getAllMappedRisksWithPhases")

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Risks with active phases fetched successfully"
    assert any(risk["risk_assessment_name"] == "Risk A" for risk in data["data"])
    assert any(phase["phase_name"] == "Phase 1" for risk in data["data"] for phase in risk["phases"])


@pytest.mark.anyio
async def test_get_all_mapped_risks_with_phases_empty(async_client: AsyncClient):
    response = await async_client.get("/master/getAllMappedRisksWithPhases")

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No active risk-phase mappings found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_mapped_risks_with_phases_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.risk_phase_map_service.database.fetch_all", side_effect=Exception("DB error"))

    response = await async_client.get("/master/getAllMappedRisksWithPhases")

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []

# ========================================================
# POST /master/mapRiskToPhases
# ========================================================
@pytest.mark.anyio
async def test_map_risk_to_phases_success_insert_and_activate(async_client: AsyncClient):
    risk_id = await insert_risk("Risk B")
    phase1 = await insert_phase("Phase X")
    phase2 = await insert_phase("Phase Y")

    payload = {"risk_assessment_id": risk_id, "phase_ids": [phase1, phase2]}
    response = await async_client.post("/master/mapRiskToPhases", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Risk to phase mapping updated successfully"


@pytest.mark.anyio
async def test_map_risk_to_phases_invalid_risk_id(async_client: AsyncClient):
    payload = {"risk_assessment_id": 0, "phase_ids": [1]}
    response = await async_client.post("/master/mapRiskToPhases", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "Valid risk_assessment_id is required"


@pytest.mark.anyio
async def test_map_risk_to_phases_invalid_phase_ids(async_client: AsyncClient):
    risk_id = await insert_risk("Risk C")
    payload = {"risk_assessment_id": risk_id, "phase_ids": []}
    response = await async_client.post("/master/mapRiskToPhases", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "Valid phase_ids is required"


@pytest.mark.anyio
async def test_map_risk_to_phases_deactivate(async_client: AsyncClient):
    risk_id = await insert_risk("Risk D")
    phase1 = await insert_phase("Phase Active")
    phase2 = await insert_phase("Phase Remove")

    # Active mappings
    await insert_risk_phase_mapping(risk_id, phase1, is_active=True)
    await insert_risk_phase_mapping(risk_id, phase2, is_active=True)

    # Keep only phase1 active
    payload = {"risk_assessment_id": risk_id, "phase_ids": [phase1]}
    response = await async_client.post("/master/mapRiskToPhases", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Risk to phase mapping updated successfully"


@pytest.mark.anyio
async def test_map_risk_to_phases_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.risk_phase_map_service.database.fetch_all", side_effect=Exception("DB fail"))

    payload = {"risk_assessment_id": 1, "phase_ids": [1]}
    response = await async_client.post("/master/mapRiskToPhases", json=payload)

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []
