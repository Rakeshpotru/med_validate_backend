import pytest
from fastapi.responses import JSONResponse
from app.services.transaction import user_role_mapping_service as service
from app.db.database import database
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.master.user_roles import user_roles_table
from unittest.mock import patch
from datetime import datetime

# -----------------------
# Helper functions
# -----------------------
async def insert_role(role_id=1, role_name="Admin"):
    query = user_roles_table.insert().values(
        role_id=role_id,
        role_name=role_name,
        is_active=True
    )
    await database.execute(query)
    return role_id

async def insert_user_role(user_id=1, role_id=1, is_active=True):
    query = user_role_mapping_table.insert().values(
        user_id=user_id,
        role_id=role_id,
        is_active=is_active
    ).returning(user_role_mapping_table.c.user_role_map_id)
    return await database.fetch_val(query)

# -----------------------
# Tests for create_user_role_mappings
# -----------------------
@pytest.mark.anyio
async def test_create_user_role_mappings_new_role():
    role_id = await insert_role(10, "TestRole")
    data = type("Payload", (), {"user_id": 100, "role_ids": [10]})()
    resp: JSONResponse = await service.create_user_role_mappings(data)
    assert resp.status_code == 200
    assert "assigned to user" in resp.body.decode()

@pytest.mark.anyio
async def test_create_user_role_mappings_existing_active():
    role_id = await insert_role(11, "ActiveRole")
    user_role_map_id = await insert_user_role(user_id=101, role_id=11, is_active=True)
    data = type("Payload", (), {"user_id": 101, "role_ids": [11]})()
    resp: JSONResponse = await service.create_user_role_mappings(data)
    assert resp.status_code == 200
    assert "already assigned" in resp.body.decode()

@pytest.mark.anyio
async def test_create_user_role_mappings_existing_inactive():
    role_id = await insert_role(12, "InactiveRole")
    user_role_map_id = await insert_user_role(user_id=102, role_id=12, is_active=False)
    data = type("Payload", (), {"user_id": 102, "role_ids": [12]})()
    resp: JSONResponse = await service.create_user_role_mappings(data)
    assert resp.status_code == 200
    assert "reactivated" in resp.body.decode()

@pytest.mark.anyio
async def test_create_user_role_mappings_non_existent_role():
    data = type("Payload", (), {"user_id": 103, "role_ids": [999]})()
    resp: JSONResponse = await service.create_user_role_mappings(data)
    assert resp.status_code == 200
    assert "does not exist" in resp.body.decode()

# -----------------------
# Tests for get_roles_by_user_id
# -----------------------
@pytest.mark.anyio
async def test_get_roles_by_user_id_found():
    role_id = await insert_role(20, "Role20")
    await insert_user_role(user_id=200, role_id=20)
    resp: JSONResponse = await service.get_roles_by_user_id(200)
    assert resp.status_code == 200
    assert "Role20" in resp.body.decode()

@pytest.mark.anyio
async def test_get_roles_by_user_id_not_found():
    resp: JSONResponse = await service.get_roles_by_user_id(9999)
    assert resp.status_code == 404
    assert "No roles found" in resp.body.decode()

# -----------------------
# Tests for delete_user_role_mapping
# -----------------------
@pytest.mark.anyio
async def test_delete_user_role_mapping_success():
    role_id = await insert_role(30, "Role30")
    user_role_map_id = await insert_user_role(user_id=300, role_id=30)
    resp: JSONResponse = await service.delete_user_role_mapping(300, 30)
    assert resp.status_code == 200
    assert "deactivated successfully" in resp.body.decode()

@pytest.mark.anyio
async def test_delete_user_role_mapping_already_inactive():
    role_id = await insert_role(31, "Role31")
    user_role_map_id = await insert_user_role(user_id=301, role_id=31, is_active=False)
    resp: JSONResponse = await service.delete_user_role_mapping(301, 31)
    assert resp.status_code == 200
    assert "already inactive" in resp.body.decode()

@pytest.mark.anyio
async def test_delete_user_role_mapping_not_found():
    resp: JSONResponse = await service.delete_user_role_mapping(999, 999)
    assert resp.status_code == 404
    assert "No mapping found" in resp.body.decode()



# -----------------------
# Line 142-144: get_roles_by_user_id no roles
# -----------------------
@pytest.mark.anyio
async def test_get_roles_by_user_id_no_rows():
    # Mock database.fetch_all to return empty list
    with patch("app.services.transaction.user_role_mapping_service.database.fetch_all", return_value=[]):
        resp: JSONResponse = await service.get_roles_by_user_id(9999)
        assert resp.status_code == 404
        assert "No roles found" in resp.body.decode()

# -----------------------
# Line 212-214: delete_user_role_mapping exception
# -----------------------
@pytest.mark.anyio
async def test_delete_user_role_mapping_exception():
    # Mock database.fetch_one to raise exception
    with patch("app.services.transaction.user_role_mapping_service.database.fetch_one", side_effect=Exception("DB error")):
        resp: JSONResponse = await service.delete_user_role_mapping(1, 1)
        assert resp.status_code == 500
        assert "An error occurred" in resp.body.decode()