# tests/test_change_request_service.py
import os
import json
import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.transaction.change_request import change_request_table
from app.db.transaction.projects import projects
from app.db.transaction.projects_user_mapping import projects_user_mapping_table
from app.db.transaction.json_template_transactions import json_template_transactions

UPLOAD_FOLDER = "change_request_files"


# --- Helper functions ---
async def insert_project(project_name="Test Project", is_active=True):
    query = projects.insert().values(project_name=project_name, is_active=is_active)
    return await database.execute(query)


async def insert_json_template(template_json: dict = None):
    if template_json is None:
        template_json = {"sections": []}
    # store as JSON string or text depending on your schema - tests assume JSON/text is fine
    query = json_template_transactions.insert().values(template_json=json.dumps(template_json))
    return await database.execute(query)


async def insert_projects_user_mapping(project_id: int, user_id: int = 1, is_active: bool = True):
    query = projects_user_mapping_table.insert().values(
        project_id=project_id, user_id=user_id, is_active=is_active
    )
    return await database.execute(query)


async def insert_change_request(
    project_id: int,
    transaction_template_id: int = None,
    change_request_code: str = "CR_CODE",
    change_request_file: str = None,
    is_verified: bool = False,
    reject_reason: str = None
):
    query = change_request_table.insert().values(
        project_id=project_id,
        change_request_code=change_request_code,
        change_request_file=change_request_file,
        is_verified=is_verified,
        transaction_template_id=transaction_template_id,
        reject_reason=reject_reason
    )
    return await database.execute(query)


# --- API helper requests ---
async def get_unverified_change_requests_request(async_client: AsyncClient):
    return await async_client.get("/transaction/getUnverifiedChangeRequests")


async def get_change_request_file_request(async_client: AsyncClient, file_name: str):
    return await async_client.get(f"/transaction/getChangeRequestFile?file_name={file_name}")


async def update_change_request_verification_request(async_client: AsyncClient, payload: dict):
    return await async_client.post("/transaction/updateChangeRequestVerificationStatus", json=payload)


# --- Tests ---
@pytest.mark.anyio
async def test_get_unverified_change_requests_success(async_client: AsyncClient):
    # Create project + mapping + template + change request
    project_id = await insert_project(project_name="P1", is_active=True)
    template_id = await insert_json_template({"some": "template"})
    await insert_projects_user_mapping(project_id=project_id, user_id=1, is_active=True)
    cr_id = await insert_change_request(
        project_id=project_id,
        transaction_template_id=template_id,
        change_request_code="CR1",
        change_request_file=None,
        is_verified=False,
        reject_reason=None
    )

    response = await get_unverified_change_requests_request(async_client)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Unverified change requests fetched successfully"
    assert isinstance(data["data"], list)
    # at least one record and expected keys present
    assert any(item["change_request_id"] == cr_id for item in data["data"])
    sample = data["data"][0]
    expected_keys = {
        "change_request_id",
        "change_request_code",
        "change_request_file",
        "reject_reason",
        "transaction_template_id",
        "change_request_json",
        "project_id",
        "project_name",
        "is_verified",
    }
    assert expected_keys.issubset(set(sample.keys()))


@pytest.mark.anyio
async def test_get_unverified_change_requests_empty(async_client: AsyncClient):
    # Ensure no change requests / mappings exist that match user_id=1
    response = await get_unverified_change_requests_request(async_client)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No unverified change requests found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_unverified_change_requests_internal_error(mocker, async_client: AsyncClient):
    # Patch database.fetch_all to raise an exception
    mocker.patch("app.services.transaction.change_request_service.database.fetch_all", side_effect=Exception("DB error"))

    response = await get_unverified_change_requests_request(async_client)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# ---------- getChangeRequestFile tests ----------
@pytest.mark.anyio
async def test_get_change_request_file_missing_name(async_client: AsyncClient):
    response = await async_client.get("/transaction/getChangeRequestFile?file_name=")
    # service returns 400 for missing/empty name
    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "File name is required"
    assert data["data"] is None


@pytest.mark.anyio
async def test_get_change_request_file_not_found(async_client: AsyncClient):
    # Ensure file doesn't exist
    fname = "non_existent_file.bin"
    # Make sure file not present
    path = os.path.join(UPLOAD_FOLDER, fname)
    if os.path.exists(path):
        os.remove(path)

    response = await get_change_request_file_request(async_client, fname)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "File not found"
    assert data["data"] is None


@pytest.mark.anyio
async def test_get_change_request_file_success(async_client: AsyncClient):
    # Create upload folder and a test file
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    fname = "test_cr_file.bin"
    path = os.path.join(UPLOAD_FOLDER, fname)
    with open(path, "wb") as f:
        f.write(b"dummy content")

    try:
        response = await get_change_request_file_request(async_client, fname)
        # FileResponse should return 200 and binary content
        assert response.status_code == 200
        content = await response.aread() if hasattr(response, "aread") else response.content
        # ensure we received the file contents
        assert b"dummy content" in content
    finally:
        # cleanup
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.anyio
async def test_get_change_request_file_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.change_request_service.os.path.isfile", side_effect=Exception("os error"))

    response = await get_change_request_file_request(async_client, "anyfile.bin")
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] is None


# ---------- updateChangeRequestVerificationStatus tests ----------
@pytest.mark.anyio
async def test_update_change_request_verification_missing_id(async_client: AsyncClient):
    # omit change_request_id -> expect 422 from FastAPI validation
    payload = {"is_verified": True, "verified_by": 1}
    response = await update_change_request_verification_request(async_client, payload)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_update_change_request_verification_not_found(async_client: AsyncClient):
    payload = {
        "change_request_id": 999999,
        "is_verified": True,
        "verified_by": 1,
        "reject_reason": None
    }
    response = await update_change_request_verification_request(async_client, payload)
    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "Change Request not found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_update_change_request_verification_success(async_client: AsyncClient):
    # Prepare project + mapping + change request
    project_id = await insert_project("P_for_update", is_active=True)
    await insert_projects_user_mapping(project_id=project_id, user_id=1, is_active=True)
    cr_id = await insert_change_request(project_id=project_id, change_request_code="CR_UPD", is_verified=False)

    payload = {
        "change_request_id": cr_id,
        "is_verified": True,
        "verified_by": 1,
        "reject_reason": None
    }
    response = await update_change_request_verification_request(async_client, payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Change request verification status updated successfully"
    assert data["data"]["change_request_id"] == cr_id
    assert data["data"]["is_verified"] is True

    # ensure DB updated (fetch row)
    row = await database.fetch_one(change_request_table.select().where(change_request_table.c.change_request_id == cr_id))
    assert row is not None
    assert row["is_verified"] is True
    # verified_by and verified_date should be set
    assert row["verified_by"] == 1
    assert row["verified_date"] is not None


@pytest.mark.anyio
async def test_update_change_request_verification_internal_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.transaction.change_request_service.database.fetch_one", side_effect=Exception("DB error"))
    payload = {
        "change_request_id": 1,
        "is_verified": True,
        "verified_by": 1,
        "reject_reason": None
    }
    response = await update_change_request_verification_request(async_client, payload)
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []
