import pytest
from httpx import AsyncClient

# --- GET API Tests for /master/getAllTestingAssetTypes ---


@pytest.mark.anyio
async def test_get_all_testing_asset_types_success_with_data(mocker, async_client: AsyncClient):
    """
    Explicitly test the success scenario.
    Covers the 'rows found' path (lines 33–36 in the service).
    """
    mock_rows = [
        {"asset_id": 1, "asset_name": "Compressor", "is_active": True},
        {"asset_id": 2, "asset_name": "Pump", "is_active": True},
    ]

    # Mock DB response with valid rows
    mocker.patch(
        "app.services.testing_asset_types_service.database.fetch_all",
        return_value=mock_rows,
    )

    # Mock schema model behavior (simulate Pydantic response model)
    mocker.patch(
        "app.services.testing_asset_types_service.TestingAssetTypeResponse",
        side_effect=lambda **kw: type("MockModel", (), {"dict": lambda self: kw})(),
    )

    response = await async_client.get("/master/getAllTestingAssetTypes")

    assert response.status_code == 200
    data = response.json()

    assert data["status_code"] == 200
    assert data["message"] == "Testing asset types fetched successfully"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert all("asset_name" in d for d in data["data"])


@pytest.mark.anyio
async def test_get_all_testing_asset_types_not_found(mocker, async_client: AsyncClient):
    """
    ❌ Test when the DB returns no active asset types.
    Covers the 404 path.
    """
    mocker.patch(
        "app.services.testing_asset_types_service.database.fetch_all",
        return_value=[],
    )

    response = await async_client.get("/master/getAllTestingAssetTypes")
    assert response.status_code == 404

    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No testing asset types found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_testing_asset_types_internal_server_error(mocker, async_client: AsyncClient):
    """
     Test when an exception is raised while fetching data.
    Covers the exception path (500).
    """
    mocker.patch(
        "app.services.testing_asset_types_service.database.fetch_all",
        side_effect=Exception("DB connection error"),
    )

    response = await async_client.get("/master/getAllTestingAssetTypes")
    assert response.status_code == 500

    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_testing_asset_types_generic_call(async_client: AsyncClient):
    """
     Generic smoke test without mocking.
    Allows API to hit the real database if available.
    Ensures valid response shape for any status.
    """
    response = await async_client.get("/master/getAllTestingAssetTypes")
    assert response.status_code in (200, 404, 500)

    data = response.json()
    assert "status_code" in data
    assert "message" in data
    assert "data" in data

    if response.status_code == 200:
        assert isinstance(data["data"], list)
        assert data["message"] == "Testing asset types fetched successfully"
    elif response.status_code == 404:
        assert data["message"] == "No testing asset types found"
    elif response.status_code == 500:
        assert data["message"] == "Internal server error"
