import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock
from app.db.database import database
from fastapi import Request

# --------------------------------------------------------------------
# 1. GET /master/by-template-type
# --------------------------------------------------------------------
@pytest.mark.anyio
async def test_get_latest_template_success(mocker, async_client: AsyncClient):
    """
    Should return 200 and latest template.
    """

    mock_row = {
        "template_id": 1,
        "template_name": "Risk Template",
        "template_type_id": 5,
        "json_template": {"a": 1},
        "created_by": 2,
        "created_date": "2025-01-01T00:00:00",
        "template_version": 3.0,
    }

    mocker.patch.object(database, "fetch_one", return_value=mock_row)

    response = await async_client.get("/master/by-template-type?template_type_id=5")
    data = response.json()

    assert response.status_code == 200
    assert data["data"]["template_id"] == 1
    assert data["data"]["template_version"] == 3.0


@pytest.mark.anyio
async def test_get_latest_template_not_found(mocker, async_client: AsyncClient):
    """Should return 404 when no data exists."""

    mocker.patch.object(database, "fetch_one", return_value=None)

    response = await async_client.get("/master/by-template-type?template_type_id=5")
    assert response.status_code == 404
    assert response.json()["message"] == "No templates found for this template_type_id"


@pytest.mark.anyio
async def test_get_latest_template_missing_param(async_client: AsyncClient):
    """Missing template_type_id should return 400."""
    response = await async_client.get("/master/by-template-type")
    assert response.status_code == 422  # FastAPI validation, because param required


# --------------------------------------------------------------------
# 2. POST /master/save
# --------------------------------------------------------------------
@pytest.mark.anyio
async def test_save_json_template_success(mocker, async_client: AsyncClient):
    """Should return 201 and created transaction_template_id."""

    # Mock DB insert
    mocker.patch.object(database, "execute", return_value=99)

    # Mock user in request.state
    class DummyState:
        user = {"user_id": 10}

    mocker.patch("app.routers.risk_assessment_template_router.Request.state", DummyState())

    payload = {"name": "test", "fields": []}

    response = await async_client.post("/master/save", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["transaction_template_id"] == 99




@pytest.mark.anyio
async def test_save_json_template_missing_json(async_client: AsyncClient):
    """Missing body should return FastAPI validation error."""

    response = await async_client.post("/master/save", json=None)
    assert response.status_code == 422  # Body is required


# --------------------------------------------------------------------
# 3. GET /master/json-template/{id}
# --------------------------------------------------------------------
@pytest.mark.anyio
async def test_get_json_template_by_id_success(mocker, async_client: AsyncClient):
    """Should return data for valid ID."""

    mock_row = {
        "transaction_template_id": 55,
        "created_by": 10,
        "template_json": {"abc": 123},
        "created_date": "2025-01-01T00:00:00",
    }

    mocker.patch.object(database, "fetch_one", return_value=mock_row)

    response = await async_client.get("/master/json-template/55")
    data = response.json()

    assert response.status_code == 200
    assert data["data"]["transaction_template_id"] == 55


@pytest.mark.anyio
async def test_get_json_template_by_id_not_found(mocker, async_client: AsyncClient):
    """Should return 404 when no row found."""

    mocker.patch.object(database, "fetch_one", return_value=None)

    response = await async_client.get("/master/json-template/778")
    assert response.status_code == 404
    assert response.json()["message"] == "No template found for id 778"
