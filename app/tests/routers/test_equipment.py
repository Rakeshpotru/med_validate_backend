import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.master.equipment import equipment_list_table


# --- Helper functions ---
async def get_all_equipments_request(async_client: AsyncClient):
    return await async_client.get("/master/equipments")


async def insert_equipment(name="Test Equipment", is_active=True, created_by=1):
    query = equipment_list_table.insert().values(
        equipment_name=name,
        is_active=is_active,
        created_by=created_by
    )
    return await database.execute(query)


# --- GET Tests ---
@pytest.mark.anyio
async def test_get_all_equipments_success(async_client: AsyncClient):
    await insert_equipment(name="Equipment A")
    await insert_equipment(name="Equipment B")

    response = await get_all_equipments_request(async_client)

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 2
    assert all("equipment_name" in eq for eq in data["data"])


@pytest.mark.anyio
async def test_get_all_equipments_empty(async_client: AsyncClient):
    response = await get_all_equipments_request(async_client)
    # could be 404 (service logic) or 200 with empty list
    assert response.status_code in (200, 404)


@pytest.mark.anyio
async def test_get_all_equipments_only_inactive(async_client: AsyncClient):
    await insert_equipment(name="Inactive Equipment", is_active=False)
    response = await get_all_equipments_request(async_client)
    assert response.status_code in (200, 404)


@pytest.mark.anyio
async def test_get_all_equipments_explicit_not_found(mocker, async_client: AsyncClient):
    mocker.patch("app.services.equipment_service.database.fetch_all", return_value=[])
    response = await get_all_equipments_request(async_client)
    assert response.status_code == 404
    data = response.json()
    assert data["message"] == "No equipments found"


@pytest.mark.anyio
async def test_get_all_equipments_internal_server_error(mocker, async_client: AsyncClient):
    mocker.patch("app.services.equipment_service.database.fetch_all", side_effect=Exception("DB error"))
    response = await get_all_equipments_request(async_client)
    assert response.status_code == 500


# --- POST Tests ---
@pytest.mark.anyio
async def test_create_equipment_success(mocker, async_client: AsyncClient):
    """
    Test successful equipment creation.
    Covers insertion path and returns 201.
    """
    # Mock asset type exists
    mocker.patch(
        "app.services.equipment_service.database.fetch_one",
        side_effect=[
            {"asset_id": 1, "is_active": True},  # asset type valid
            None,  # no existing equipment
            {"equipment_id": 10}  # inserted new equipment
        ]
    )

    payload = {
        "equipment_name": "New Equipment",
        "created_by": 1,
        "asset_type_id": 1
    }

    response = await async_client.post("/master/create-equipments", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["status_code"] == 201
    assert data["message"] == "Equipment created successfully"
    assert data["data"]["equipment_name"] == "New Equipment"
    assert data["data"]["asset_type_id"] == 1
    assert data["data"]["created_by"] == 1


@pytest.mark.anyio
async def test_create_equipment_duplicate_active(mocker, async_client: AsyncClient):
    """
    Test when equipment already exists and is active.
    Should return 409 Conflict.
    """
    mocker.patch(
        "app.services.equipment_service.database.fetch_one",
        side_effect=[
            {"asset_id": 1, "is_active": True},  # asset type exists
            {"equipment_id": 5, "is_active": True}  # existing active equipment
        ]
    )

    payload = {
        "equipment_name": "Duplicate Equipment",
        "created_by": 1,
        "asset_type_id": 1
    }

    response = await async_client.post("/master/create-equipments", json=payload)
    assert response.status_code == 409

    data = response.json()
    assert data["status_code"] == 409
    assert "already exists" in data["message"]


@pytest.mark.anyio
async def test_create_equipment_reactivate_inactive(mocker, async_client: AsyncClient):
    """
     Test when equipment exists but inactive.
    Should reactivate and return 200.
    """
    mocker.patch(
        "app.services.equipment_service.database.fetch_one",
        side_effect=[
            {"asset_id": 1, "is_active": True},  # valid asset type
            {"equipment_id": 7, "is_active": False},  # existing inactive
            {"equipment_id": 7}  # updated_row (reactivated)
        ]
    )

    payload = {
        "equipment_name": "Old Equipment",
        "created_by": 2,
        "asset_type_id": 1
    }

    response = await async_client.post("/master/create-equipments", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Equipment reactivated successfully"
    assert data["data"]["equipment_id"] == 7
    assert data["data"]["updated_by"] == 2


@pytest.mark.anyio
async def test_create_equipment_invalid_asset_type(mocker, async_client: AsyncClient):
    """
     Test invalid asset_type_id (asset type not found).
    Should return 400.
    """
    mocker.patch(
        "app.services.equipment_service.database.fetch_one",
        return_value=None
    )

    payload = {
        "equipment_name": "Invalid Asset Equipment",
        "created_by": 1,
        "asset_type_id": 99
    }

    response = await async_client.post("/master/create-equipments", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["status_code"] == 400
    assert "Invalid asset_type_id" in data["message"]


@pytest.mark.anyio
async def test_create_equipment_invalid_created_by(async_client: AsyncClient):
    """
     Test created_by = 0.
    Should fail with 400.
    """
    payload = {
        "equipment_name": "Invalid Creator",
        "created_by": 0,
        "asset_type_id": 1
    }

    response = await async_client.post("/master/create-equipments", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "created_by cannot be 0"
    assert data["data"] == []





# -------------------------------------------------------------------
# PUT /master/update-equipments/{id}
# -------------------------------------------------------------------
@pytest.mark.anyio
async def test_update_equipment_success(async_client: AsyncClient):
    """✅ Should update equipment name successfully."""
    eq_id = await insert_equipment(name="Old Equipment")
    payload = {"equipment_name": "Updated Equipment", "updated_by": 2, "asset_type_id": 1}

    response = await async_client.put(f"/master/update-equipments/{eq_id}", json=payload)
    data = response.json()

    assert response.status_code == 200
    assert data["message"] == "Equipment updated successfully"
    assert data["data"]["equipment_name"] == "Updated Equipment"


@pytest.mark.anyio
async def test_update_equipment_not_found(async_client: AsyncClient):
    """❌ Should return 404 when equipment does not exist."""
    payload = {"equipment_name": "Does Not Exist", "updated_by": 1, "asset_type_id": 1}
    response = await async_client.put("/master/update-equipments/999999", json=payload)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_update_equipment_inactive(async_client: AsyncClient):
    """❌ Should fail to update inactive equipment."""
    eq_id = await insert_equipment(name="Inactive Equipment", is_active=False)
    payload = {"equipment_name": "Try Update", "updated_by": 2, "asset_type_id": 1}

    response = await async_client.put(f"/master/update-equipments/{eq_id}", json=payload)
    data = response.json()

    assert response.status_code == 400
    assert data["message"] == "Equipment is inactive"


@pytest.mark.anyio
async def test_update_equipment_internal_error(mocker, async_client: AsyncClient):
    """❌ Should return 500 if DB operation fails."""
    eq_id = await insert_equipment(name="Err Update")
    mocker.patch("app.services.equipment_service.database.fetch_one", side_effect=Exception("DB error"))

    payload = {"equipment_name": "ErrorName", "updated_by": 2, "asset_type_id": 1}
    response = await async_client.put(f"/master/update-equipments/{eq_id}", json=payload)

    assert response.status_code == 500
    assert response.json()["message"] == "Internal server error"

# --- DELETE Tests ---
@pytest.mark.anyio
async def test_delete_equipment_success(async_client: AsyncClient):
    eq_id = await insert_equipment(name="To Delete", is_active=True)
    payload = {"updated_by": 2}

    response = await async_client.request(
        "DELETE",
        f"/master/delete-equipments/{eq_id}",
        json=payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["data"]["equipment_id"] == eq_id


@pytest.mark.anyio
async def test_delete_equipment_not_found(async_client: AsyncClient):
    payload = {"updated_by": 2}

    response = await async_client.request(
        "DELETE",
        "/master/delete-equipments/999999",
        json=payload
    )

    assert response.status_code == 404
    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "Equipment not found"


@pytest.mark.anyio
async def test_delete_equipment_already_inactive(async_client: AsyncClient):
    eq_id = await insert_equipment(name="Inactive Equipment", is_active=False)
    payload = {"updated_by": 2}

    response = await async_client.request(
        "DELETE",
        f"/master/delete-equipments/{eq_id}",
        json=payload
    )

    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "Equipment is already inactive"


@pytest.mark.anyio
async def test_delete_equipment_internal_server_error(mocker, async_client: AsyncClient):
    eq_id = await insert_equipment(name="Cause Error", is_active=True)
    payload = {"updated_by": 2}

    mocker.patch(
        "app.services.equipment_service.database.fetch_one",
        side_effect=Exception("DB error")
    )

    response = await async_client.request(
        "DELETE",
        f"/master/delete-equipments/{eq_id}",
        json=payload
    )

    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
