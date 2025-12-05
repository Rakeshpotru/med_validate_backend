import pytest
from httpx import AsyncClient
from datetime import datetime
from typing import Dict, Any

# --- GET API Tests for /master/getAllTemplateTypes ---
# (Assuming these pass; included for completeness)

@pytest.mark.anyio
async def test_get_all_template_types_success_with_data(mocker, async_client: AsyncClient):
    """
    Explicitly test the success scenario.
    Covers the 'rows found' path in get_all_template_types.
    """
    mock_rows = [
        {
            "template_type_id": 1,
            "template_type_name": "Type A",
            "is_active": True,
            "template_format_type_id": 1,
            "format_name": "JSON",
            "section": True,
            "weightage": True,
            "table": True,
        },
        {
            "template_type_id": 2,
            "template_type_name": "Type B",
            "is_active": True,
            "template_format_type_id": 2,
            "format_name": "XML",
            "section": False,
            "weightage": True,
            "table": False,
        },
    ]

    # Mock DB response with valid rows
    mocker.patch(
        "app.services.template_type_service.database.fetch_all",
        return_value=mock_rows,
    )

    # Mock schema model behavior (simulate Pydantic response model)
    mocker.patch(
        "app.services.template_type_service.TemplateTypeFullResponse",
        side_effect=lambda **kw: type("MockModel", (), {"model_dump": lambda self, **kwargs: kw})(),
    )

    response = await async_client.get("/master/getAllTemplateTypes")

    assert response.status_code == 200
    data = response.json()

    assert data["status_code"] == 200
    assert data["message"] == "Active template types fetched successfully"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert all("template_type_name" in d for d in data["data"])


@pytest.mark.anyio
async def test_get_all_template_types_not_found(mocker, async_client: AsyncClient):
    """
    Test when the DB returns no active template types.
    Covers the 404 path.
    """
    mocker.patch(
        "app.services.template_type_service.database.fetch_all",
        return_value=[],
    )

    response = await async_client.get("/master/getAllTemplateTypes")
    assert response.status_code == 404

    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No active template types found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_template_types_internal_server_error(mocker, async_client: AsyncClient):
    """
    Test when an exception is raised while fetching data.
    Covers the exception path (500).
    """
    mocker.patch(
        "app.services.template_type_service.database.fetch_all",
        side_effect=Exception("DB connection error"),
    )

    response = await async_client.get("/master/getAllTemplateTypes")
    assert response.status_code == 500

    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_template_types_generic_call(async_client: AsyncClient):
    """
    Generic smoke test without mocking.
    Allows API to hit the real database if available.
    Ensures valid response shape for any status.
    """
    response = await async_client.get("/master/getAllTemplateTypes")
    assert response.status_code in (200, 404, 500)

    data = response.json()
    assert "status_code" in data
    assert "message" in data
    assert "data" in data

    if response.status_code == 200:
        assert isinstance(data["data"], list)
        assert data["message"] == "Active template types fetched successfully"
    elif response.status_code == 404:
        assert data["message"] == "No active template types found"
    elif response.status_code == 500:
        assert data["message"] == "Internal server error"


# --- POST API Tests for /master/createJsonTemplate ---


@pytest.mark.anyio
async def test_create_json_template_success(mocker, async_client: AsyncClient):
    """
    Explicitly test the success scenario.
    Covers the insert and return path in create_json_template.
    """
    input_data = {
        "template_name": "Test Template",
        "template_type_id": 1,
        "json_template": {"key": "value"},
        "created_by": 123,
    }

    mock_type_result = {"template_type_id": 1}
    mock_insert_result = {
        "template_id": 1,
        "template_name": input_data["template_name"],
        "template_type_id": input_data["template_type_id"],
        "json_template": input_data["json_template"],
        "created_by": input_data["created_by"],
        "created_date": datetime(2023, 1, 1),
        "template_version": 1.0,
    }

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        side_effect=[mock_type_result, mock_insert_result],
    )
    mocker.patch(
        "app.services.template_type_service.database.fetch_val",
        return_value=None,
    )

    # Mock schema model behavior
    mocker.patch(
        "app.services.template_type_service.JsonTemplateResponse",
        side_effect=lambda **kw: type("MockModel", (), {"model_dump": lambda self, **kwargs: {k: v.isoformat() if isinstance(v, datetime) else v for k, v in kw.items()}})(),
    )

    response = await async_client.post("/master/createJsonTemplate", json=input_data)

    assert response.status_code == 201
    data = response.json()

    assert data["status_code"] == 201
    assert data["message"] == "JSON template created successfully"
    assert data["data"]["template_name"] == input_data["template_name"]
    assert data["data"]["template_version"] == 1.0


@pytest.mark.anyio
async def test_create_json_template_invalid_type(mocker, async_client: AsyncClient):
    """
    Test when template_type_id is invalid or inactive (400).
    """
    input_data = {
        "template_name": "Test Template",
        "template_type_id": 999,
        "json_template": {"key": "value"},
        "created_by": 123,
    }

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value=None,
    )

    response = await async_client.post("/master/createJsonTemplate", json=input_data)
    assert response.status_code == 400

    data = response.json()
    assert data["status_code"] == 400
    assert data["message"] == "Invalid or inactive template type"
    assert data["data"] is None


@pytest.mark.anyio
async def test_create_json_template_internal_server_error(mocker, async_client: AsyncClient):
    """
    Test when an exception is raised during creation (500).
    """
    input_data = {
        "template_name": "Test Template",
        "template_type_id": 1,
        "json_template": {"key": "value"},
        "created_by": 123,
    }

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        side_effect=Exception("DB error"),
    )

    response = await async_client.post("/master/createJsonTemplate", json=input_data)
    assert response.status_code == 500

    data = response.json()
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] is None


@pytest.mark.anyio
async def test_create_json_template_generic_call(async_client: AsyncClient):
    """
    Generic smoke test without mocking.
    Ensures valid response shape for any status (201, 400, 500).
    """
    input_data = {
        "template_name": "Smoke Test",
        "template_type_id": 1,
        "json_template": {"key": "value"},
        "created_by": 123,
    }
    response = await async_client.post("/master/createJsonTemplate", json=input_data)
    assert response.status_code in (201, 400, 500)

    data = response.json()
    assert "status_code" in data
    assert "message" in data
    assert "data" in data

    if response.status_code == 201:
        assert data["message"] == "JSON template created successfully"
        assert isinstance(data["data"], dict)
    elif response.status_code == 400:
        assert "Invalid" in data["message"]
    elif response.status_code == 500:
        assert data["message"] == "Internal server error"


# --- GET API Tests for /master/getJsonTemplate/{template_id} ---


@pytest.mark.anyio
async def test_get_json_template_success(mocker, async_client: AsyncClient):
    """
    Explicitly test the success scenario.
    Covers the row found path in get_json_template_by_id.
    """
    template_id = 1
    mock_row = {
        "template_id": template_id,
        "template_name": "Test Template",
        "template_type_id": 1,
        "json_template": {"key": "value"},
        "created_by": 123,
        "created_date": datetime(2023, 1, 1),
        "template_version": 1.0,
    }

    # Mock DB response with valid row
    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value=mock_row,
    )

    # Mock schema model behavior
    mocker.patch(
        "app.services.template_type_service.JsonTemplateResponse",
        side_effect=lambda **kw: type("MockModel", (), {"model_dump": lambda self, **kwargs: {k: v.isoformat() if isinstance(v, datetime) else v for k, v in kw.items()}})(),
    )

    response = await async_client.get(f"/master/getJsonTemplate/{template_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["status_code"] == 200
    assert data["message"] == "JSON template fetched successfully"
    assert data["data"]["template_id"] == template_id
    assert isinstance(data["data"]["json_template"], dict)


@pytest.mark.anyio
async def test_get_json_template_not_found(mocker, async_client: AsyncClient):
    """
    Test when the template_id is not found (404).
    """
    template_id = 999

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value=None,
    )

    response = await async_client.get(f"/master/getJsonTemplate/{template_id}")
    assert response.status_code == 404

    data = response.json()
    assert data["detail"] == "JSON template not found"


@pytest.mark.anyio
async def test_get_json_template_internal_server_error(mocker, async_client: AsyncClient):
    """
    Test when an exception is raised while fetching (500).
    """
    template_id = 1

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        side_effect=Exception("DB error"),
    )

    response = await async_client.get(f"/master/getJsonTemplate/{template_id}")
    assert response.status_code == 500

    data = response.json()
    assert data["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_get_json_template_generic_call(async_client: AsyncClient):
    """
    Generic smoke test without mocking.
    Ensures valid response shape for any status (200, 404, 500).
    """
    template_id = 1
    response = await async_client.get(f"/master/getJsonTemplate/{template_id}")
    assert response.status_code in (200, 404, 500)

    data = response.json()

    if response.status_code == 200:
        assert "status_code" in data
        assert data["status_code"] == 200
        assert data["message"] == "JSON template fetched successfully"
        assert isinstance(data["data"], dict)
    elif response.status_code == 404:
        assert "detail" in data
        assert data["detail"] == "JSON template not found"
    elif response.status_code == 500:
        assert "detail" in data
        assert data["detail"] == "Internal server error"


# --- GET API Tests for /master/getAllVersions ---


@pytest.mark.anyio
async def test_get_all_versions_success_with_data(mocker, async_client: AsyncClient):
    """
    Explicitly test the success scenario.
    Covers the 'rows found' path in get_all_versions_by_type_id.
    """
    template_type_id = 1
    mock_type_result = {"template_type_id": template_type_id}
    sample_date = datetime(2023, 1, 1)
    mock_rows = [
        {
            "template_id": 1,
            "template_name": "Version 1",
            "template_type_id": template_type_id,
            "json_template": {"key": "value1"},
            "created_by": 123,
            "created_date": sample_date,
            "template_version": 2.0,
        },
        {
            "template_id": 2,
            "template_name": "Version 2",
            "template_type_id": template_type_id,
            "json_template": {"key": "value2"},
            "created_by": 123,
            "created_date": sample_date,
            "template_version": 1.0,
        },
    ]

    # Mock fetch_one for type validation
    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value=mock_type_result,
    )

    # Mock fetch_all with valid rows
    mocker.patch(
        "app.services.template_type_service.database.fetch_all",
        return_value=mock_rows,
    )

    # Mock schema model behavior
    mocker.patch(
        "app.services.template_type_service.JsonTemplateResponse",
        side_effect=lambda **kw: type("MockModel", (), {"model_dump": lambda self, **kwargs: {k: v.isoformat() if isinstance(v, datetime) else v for k, v in kw.items()}})(),
    )

    response = await async_client.get(f"/master/getAllVersions?template_type_id={template_type_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["status_code"] == 200
    assert data["message"] == "All versions fetched successfully"
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 2
    assert all("template_version" in v for v in data["data"])


@pytest.mark.anyio
async def test_get_all_versions_invalid_type(mocker, async_client: AsyncClient):
    """
    Test when template_type_id is invalid or inactive (400).
    """
    template_type_id = 999

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value=None,
    )

    response = await async_client.get(f"/master/getAllVersions?template_type_id={template_type_id}")
    assert response.status_code == 400

    data = response.json()
    assert data["detail"] == "Invalid or inactive template type"


@pytest.mark.anyio
async def test_get_all_versions_not_found(mocker, async_client: AsyncClient):
    """
    Test when no versions found for valid type (404).
    """
    template_type_id = 1

    # Mock type validation success
    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        return_value={"template_type_id": template_type_id},
    )

    # Mock fetch_all with empty
    mocker.patch(
        "app.services.template_type_service.database.fetch_all",
        return_value=[],
    )

    response = await async_client.get(f"/master/getAllVersions?template_type_id={template_type_id}")
    assert response.status_code == 404

    data = response.json()
    assert data["status_code"] == 404
    assert data["message"] == "No versions found for this template type"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_versions_internal_server_error(mocker, async_client: AsyncClient):
    """
    Test when an exception is raised while fetching versions (500).
    """
    template_type_id = 1

    mocker.patch(
        "app.services.template_type_service.database.fetch_one",
        side_effect=Exception("DB error"),
    )

    response = await async_client.get(f"/master/getAllVersions?template_type_id={template_type_id}")
    assert response.status_code == 500

    data = response.json()
    assert data["detail"] == "Internal server error"


@pytest.mark.anyio
async def test_get_all_versions_generic_call(async_client: AsyncClient):
    """
    Generic smoke test without mocking.
    Ensures valid response shape for any status (200, 400, 404, 500).
    """
    template_type_id = 1
    response = await async_client.get(f"/master/getAllVersions?template_type_id={template_type_id}")
    assert response.status_code in (200, 400, 404, 500)

    data = response.json()

    if response.status_code == 200:
        assert "status_code" in data
        assert data["status_code"] == 200
        assert data["message"] == "All versions fetched successfully"
        assert isinstance(data["data"], list)
    elif response.status_code == 400:
        assert "detail" in data
        assert data["detail"] == "Invalid or inactive template type"
    elif response.status_code == 404:
        if "status_code" in data:
            assert data["status_code"] == 404
            assert data["message"] == "No versions found for this template type"
        else:
            assert "detail" in data
            assert "No versions" in data["detail"]
    elif response.status_code == 500:
        assert "detail" in data
        assert data["detail"] == "Internal server error"