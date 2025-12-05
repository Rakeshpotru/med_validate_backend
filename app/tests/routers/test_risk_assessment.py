import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.risk_assessment import risk_assessment_table


# --- Helper functions ---
async def get_all_risk_assessments_request(async_client: AsyncClient):
    return await async_client.get("/master/getAllRiskAssessments")

async def insert_risk_assessment(name="Test Assessment", is_active=True):
    query = risk_assessment_table.insert().values(
        risk_assessment_name=name,
        is_active=is_active
    )
    return await database.execute(query)


# --- GET Tests ---
@pytest.mark.anyio
async def test_get_all_risk_assessments_success(async_client: AsyncClient):
    await insert_risk_assessment(name="Assessment A")
    await insert_risk_assessment(name="Assessment B")

    response = await get_all_risk_assessments_request(async_client)

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Risk assessments fetched successfully"
    assert len(data["data"]) == 2
    assert all("risk_assessment_name" in ra for ra in data["data"])


@pytest.mark.anyio
async def test_get_all_risk_assessments_empty(async_client: AsyncClient):
    response = await get_all_risk_assessments_request(async_client)

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No risk assessments found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_risk_assessments_only_inactive(async_client: AsyncClient):
    await insert_risk_assessment(name="Inactive RA", is_active=False)

    response = await get_all_risk_assessments_request(async_client)

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No risk assessments found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_risk_assessments_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.risk_assessment_service.database.fetch_all", side_effect=Exception("DB error"))

    response = await get_all_risk_assessments_request(async_client)

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# --- POST Tests ---
@pytest.mark.anyio
async def test_create_risk_assessment_success(async_client: AsyncClient):
    payload = {"risk_assessment_name": "New RA", "is_active": True}
    response = await async_client.post("/master/createRiskAssessment", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status_code"] == 201
    assert data["message"] == "Risk assessment created successfully"
    assert data["data"]["risk_assessment_name"] == "New RA"


@pytest.mark.anyio
async def test_create_risk_assessment_missing_name(async_client: AsyncClient):
    payload = {"risk_assessment_name": "", "is_active": True}
    response = await async_client.post("/master/createRiskAssessment", json=payload)

    assert response.status_code == 400
    data = response.json()
    assert data["message"] == "Risk assessment name is required"


# --- PUT Tests ---
@pytest.mark.anyio
async def test_update_risk_assessment_success(async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="Old Name")
    payload = {"risk_assessment_id": ra_id, "risk_assessment_name": "Updated Name"}
    response = await async_client.put("/master/updateRiskAssessment", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Updated successfully"
    assert data["data"]["risk_assessment_name"] == "Updated Name"


@pytest.mark.anyio
async def test_update_risk_assessment_not_found(async_client: AsyncClient):
    payload = {"risk_assessment_id": 9999, "risk_assessment_name": "Name"}
    response = await async_client.put("/master/updateRiskAssessment", json=payload)

    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "Not found"


# --- DELETE Tests ---
@pytest.mark.anyio
async def test_delete_risk_assessment_success(async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="To Delete")
    payload = {"risk_assessment_id": ra_id}

    response = await async_client.request(
        method="DELETE",
        url="/master/deleteRiskAssessment",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Inactivated successfully"
    assert data["data"]["risk_assessment_id"] == ra_id
    assert data["data"]["is_active"] is False


@pytest.mark.anyio
async def test_delete_risk_assessment_already_inactive(async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="Inactive RA", is_active=False)
    payload = {"risk_assessment_id": ra_id}

    response = await async_client.request(
        method="DELETE",
        url="/master/deleteRiskAssessment",
        json=payload
    )

    assert response.status_code == 409
    data = response.json()
    assert data["status_code"] == 409
    assert data["message"] == "Already inactive"
    assert data["data"] == []

# --- POST Tests ---

@pytest.mark.anyio
async def test_create_risk_assessment_conflict_active(async_client: AsyncClient):
    # insert an active RA
    await insert_risk_assessment(name="Duplicate RA", is_active=True)
    payload = {"risk_assessment_name": "Duplicate RA", "is_active": True}

    response = await async_client.post("/master/createRiskAssessment", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert data["message"].startswith("Risk assessment 'Duplicate RA' already exists")


@pytest.mark.anyio
async def test_create_risk_assessment_reactivate_inactive(async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="Inactive RA", is_active=False)
    payload = {"risk_assessment_name": "Inactive RA", "is_active": True}

    response = await async_client.post("/master/createRiskAssessment", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"].endswith("reactivated successfully")
    assert data["data"]["risk_assessment_id"] == ra_id


# --- PUT Tests ---

@pytest.mark.anyio
async def test_update_risk_assessment_missing_id(async_client: AsyncClient):
    payload = {"risk_assessment_id": None, "risk_assessment_name": "Some Name"}
    response = await async_client.put("/master/updateRiskAssessment", json=payload)

    assert response.status_code == 400
    assert response.json()["message"] == "ID is required"


@pytest.mark.anyio
async def test_update_risk_assessment_missing_name(async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="Temp")
    payload = {"risk_assessment_id": ra_id, "risk_assessment_name": ""}
    response = await async_client.put("/master/updateRiskAssessment", json=payload)

    assert response.status_code == 400
    assert response.json()["message"] == "Name is required"


@pytest.mark.anyio
async def test_update_risk_assessment_conflict(async_client: AsyncClient):
    await insert_risk_assessment(name="ConflictName")   # no need to assign
    ra2 = await insert_risk_assessment(name="OtherName")

    payload = {"risk_assessment_id": ra2, "risk_assessment_name": "ConflictName"}
    response = await async_client.put("/master/updateRiskAssessment", json=payload)

    assert response.status_code == 409
    assert "already exists" in response.json()["message"]



# --- DELETE Tests ---

@pytest.mark.anyio
async def test_delete_risk_assessment_missing_id(async_client: AsyncClient):
    payload = {"risk_assessment_id": None}
    response = await async_client.request("DELETE", "/master/deleteRiskAssessment", json=payload)

    assert response.status_code == 400
    assert response.json()["message"] == "ID is required"


@pytest.mark.anyio
async def test_delete_risk_assessment_not_found(async_client: AsyncClient):
    payload = {"risk_assessment_id": 999999}
    response = await async_client.request("DELETE", "/master/deleteRiskAssessment", json=payload)

    assert response.status_code == 404
    assert response.json()["message"] == "Not found"


@pytest.mark.anyio
async def test_delete_risk_assessment_internal_server_error(mocker, async_client: AsyncClient):
    ra_id = await insert_risk_assessment(name="Error RA")
    mocker.patch("app.services.risk_assessment_service.database.execute", side_effect=Exception("DB error"))

    payload = {"risk_assessment_id": ra_id}
    response = await async_client.request("DELETE", "/master/deleteRiskAssessment", json=payload)

    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"
