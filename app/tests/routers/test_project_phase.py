import pytest
from unittest.mock import AsyncMock
from fastapi.responses import JSONResponse
from app.services.transaction import project_phase_service as service
from app.schemas.transaction.project_phase_schema import MapUsersToPhaseRequest, ProjectPhaseTransferRequest
import json
from pydantic import ValidationError

# ------------------------------
# map_users_to_project_phase_service
# ------------------------------

@pytest.mark.anyio
async def test_map_users_to_project_phase_validation_error():
    # Pydantic V2 validation: invalid payload should raise ValidationError
    with pytest.raises(ValidationError):
        MapUsersToPhaseRequest(project_phase_id=None, user_ids=[])

@pytest.mark.anyio
async def test_map_users_to_project_phase_insert_and_update():
    db_mock = AsyncMock()
    payload = MapUsersToPhaseRequest(project_phase_id=1, user_ids=[1, 2])

    # Mock existing rows: user 1 exists but inactive, user 2 doesn't exist
    db_mock.fetch_all.return_value = [
        {"user_id": 1, "user_is_active": False, "project_phase_user_map_id": 100}
    ]

    resp: JSONResponse = await service.map_users_to_project_phase_service(db_mock, payload)

    # Should call execute twice: one update, one insert
    assert db_mock.execute.call_count == 2
    calls_types = [type(call_args[0][0]).__name__ for call_args in db_mock.execute.call_args_list]
    assert "Update" in calls_types
    assert "Insert" in calls_types

    assert resp.status_code == 200
    data = json.loads(resp.body)["data"]
    assert set(data["user_ids"]) == {1, 2}

@pytest.mark.anyio
async def test_map_users_to_project_phase_exception():
    db_mock = AsyncMock()
    payload = MapUsersToPhaseRequest(project_phase_id=1, user_ids=[1])
    db_mock.fetch_all.side_effect = Exception("DB error")

    resp = await service.map_users_to_project_phase_service(db_mock, payload)
    assert resp.status_code == 500
    assert "Internal server error" in resp.body.decode()

# ------------------------------
# get_users_by_project_phase_id
# ------------------------------

@pytest.mark.anyio
async def test_get_users_by_project_phase_id_no_users():
    db_mock = AsyncMock()
    db_mock.fetch_all.return_value = []

    resp = await service.get_users_by_project_phase_id(db_mock, 999)
    assert resp.status_code == 404
    assert "No users found" in resp.body.decode()

@pytest.mark.anyio
async def test_get_users_by_project_phase_id_success():
    db_mock = AsyncMock()
    db_mock.fetch_all.return_value = [
        {"user_id": 1, "user_name": "Alice", "email": "alice@example.com"},
        {"user_id": 2, "user_name": "Bob", "email": "bob@example.com"}
    ]
    resp = await service.get_users_by_project_phase_id(db_mock, 1)
    assert resp.status_code == 200
    data = json.loads(resp.body)["data"]
    assert len(data) == 2
    assert data[0]["user_name"] == "Alice"

@pytest.mark.anyio
async def test_get_users_by_project_phase_id_exception():
    db_mock = AsyncMock()
    db_mock.fetch_all.side_effect = Exception("DB error")

    resp = await service.get_users_by_project_phase_id(db_mock, 1)
    assert resp.status_code == 500
    assert "Internal server error" in resp.body.decode()

# ------------------------------
# transfer_project_phase_ownership_service
# ------------------------------

@pytest.mark.anyio
async def test_transfer_project_phase_ownership_validation_error():
    with pytest.raises(ValidationError):
        ProjectPhaseTransferRequest(
            project_phase_id=None, from_user_id=1, to_user_id=2, phase_transfer_reason="Reason"
        )

@pytest.mark.anyio
async def test_transfer_project_phase_ownership_same_user_error():
    payload = ProjectPhaseTransferRequest(
        project_phase_id=1, from_user_id=1, to_user_id=1, phase_transfer_reason="Reason"
    )
    resp = await service.transfer_project_phase_ownership_service(AsyncMock(), payload)
    assert resp.status_code == 400
    assert "cannot be the same" in resp.body.decode()

@pytest.mark.anyio
async def test_transfer_project_phase_ownership_record_not_found():
    db_mock = AsyncMock()
    db_mock.fetch_one.return_value = None
    payload = ProjectPhaseTransferRequest(
        project_phase_id=1, from_user_id=1, to_user_id=2, phase_transfer_reason="Reason"
    )
    resp = await service.transfer_project_phase_ownership_service(db_mock, payload)
    assert resp.status_code == 404
    assert "No matching active record found" in resp.body.decode()

@pytest.mark.anyio
async def test_transfer_project_phase_ownership_success():
    db_mock = AsyncMock()
    db_mock.fetch_one.return_value = type("Row", (), {"project_phase_user_map_id": 123})()
    payload = ProjectPhaseTransferRequest(
        project_phase_id=1, from_user_id=1, to_user_id=2, phase_transfer_reason="Reason"
    )

    resp = await service.transfer_project_phase_ownership_service(db_mock, payload)

    # Ensure both update and insert are executed
    assert db_mock.execute.call_count == 2

    assert resp.status_code == 200
    data = json.loads(resp.body)["data"]
    assert data["from_user_id"] == 1
    assert data["to_user_id"] == 2


@pytest.mark.anyio
async def test_transfer_project_phase_ownership_exception():
    db_mock = AsyncMock()
    db_mock.fetch_one.side_effect = Exception("DB error")
    payload = ProjectPhaseTransferRequest(
        project_phase_id=1, from_user_id=1, to_user_id=2, phase_transfer_reason="Reason"
    )
    resp = await service.transfer_project_phase_ownership_service(db_mock, payload)
    assert resp.status_code == 500
    assert "Internal server error" in resp.body.decode()
