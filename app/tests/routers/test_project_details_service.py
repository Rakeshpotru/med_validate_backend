import pytest
import json
from unittest.mock import Mock
from httpx import AsyncClient


# ---------------- Utility call helpers ----------------
async def call_get_projects_by_user(async_client: AsyncClient, user_id: int):
    return await async_client.get(f"/transaction/new_getProjectsByUser/{user_id}")


async def call_get_project_details(async_client: AsyncClient, project_id: int):
    return await async_client.get(f"/transaction/new_getProjectDetails/{project_id}")


async def call_get_user_tasks(async_client: AsyncClient, user_id: int, project_id: int):
    return await async_client.get(
        f"/transaction/new_getUserTasks?user_id={user_id}&project_id={project_id}"
    )


# ---------------- Tests ----------------
@pytest.mark.anyio
async def test_get_projects_by_user_invalid_user_id(async_client: AsyncClient):
    response = await call_get_projects_by_user(async_client, 0)
    assert response.status_code == 400
    data = response.json()
    assert "invalid user_id provided" in data["message"].lower()


@pytest.mark.anyio
async def test_get_projects_by_user_not_found(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        return_value=None,
    )
    response = await call_get_projects_by_user(async_client, 123)
    assert response.status_code == 404
    data = response.json()
    assert "no active projects found" in data["message"].lower()


@pytest.mark.anyio
async def test_get_projects_by_user_json_parse_error(mocker, async_client: AsyncClient):
    bad_row = {"projects_json": "not a valid json"}
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        return_value=bad_row,
    )
    response = await call_get_projects_by_user(async_client, 456)
    assert response.status_code == 500
    data = response.json()
    assert "error parsing json" in data["message"].lower()


@pytest.mark.anyio
async def test_get_projects_by_user_success(mocker, async_client: AsyncClient):
    projects_json_str = '{"data":[{"project_id":1,"name":"Proj1"}]}'
    good_row = {"projects_json": projects_json_str}
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        return_value=good_row,
    )

    response = await call_get_projects_by_user(async_client, 789)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"].lower() == "projects fetched successfully"
    assert isinstance(data["data"]["data"], list)
    assert data["data"]["data"][0]["project_id"] == 1


@pytest.mark.anyio
async def test_get_projects_by_user_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        side_effect=Exception("DB failure"),
    )
    response = await call_get_projects_by_user(async_client, 999)
    assert response.status_code == 500


# ---------------- Project Details ----------------
@pytest.mark.anyio
async def test_get_project_details_missing_project_id(async_client: AsyncClient):
    response = await call_get_project_details(async_client, 0)
    assert response.status_code == 400
    data = response.json()
    assert "missing or invalid project_id" in data["message"].lower()


@pytest.mark.anyio
async def test_get_project_details_not_found(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        return_value=None,
    )
    response = await call_get_project_details(async_client, 55)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_project_details_success(mocker, async_client: AsyncClient):
    json_response = {
        "status_code": 200,
        "message": "Project details fetched successfully",
        "data": {"completed_percentage": 50, "project_id": 10},
    }
    mock_row = Mock()
    mock_row.response_json = json.dumps(json_response)
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        return_value=mock_row,
    )

    response = await call_get_project_details(async_client, 10)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["data"]["project_id"] == 10


@pytest.mark.anyio
async def test_get_project_details_internal_error(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_one",
        side_effect=Exception("Unexpected DB failure"),
    )
    response = await call_get_project_details(async_client, 101)
    assert response.status_code == 500


# ---------------- User Tasks ----------------
@pytest.mark.anyio
async def test_get_user_tasks_missing_user_id(async_client: AsyncClient):
    response = await call_get_user_tasks(async_client, 0, 1)
    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 400
    assert data["message"] == "User ID is required."



@pytest.mark.anyio
async def test_get_user_tasks_no_tasks(mocker, async_client: AsyncClient):
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_all",
        return_value=[],
    )
    response = await call_get_user_tasks(async_client, 11, 22)
    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 404
    assert data["message"] == "No tasks found."


@pytest.mark.anyio
async def test_get_user_tasks_json_parse_error(mocker, async_client: AsyncClient):
    bad_row = [{"tasks_json": "not json"}]
    mocker.patch(
        "app.services.transaction.project_details_service.database.fetch_all",
        return_value=bad_row,
    )
    response = await call_get_user_tasks(async_client, 33, 44)
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 500



# @pytest.mark.anyio
# async def test_get_user_tasks_success(mocker, async_client: AsyncClient):
#     # Simulated JSON string (what the DB query would actually return)
#     tasks_data = [{"task_id": 1, "task_name": "Design"}, {"task_id": 2, "task_name": "Build"}]
#     mock_data = [{"tasks_json": json.dumps(tasks_data)}]  # ✅ dict + JSON string
#
#     mocker.patch(
#         "app.services.transaction.project_details_service.database.fetch_all",
#         return_value=mock_data
#     )
#     mocker.patch(
#         "app.services.transaction.project_details_service.database.fetch_one",
#         return_value=None
#     )
#
#     response = await async_client.get(
#         "/transaction/new_getUserTasks",
#         params={"user_id": 102, "project_id": 202},
#     )
#
#     print("Response JSON:", response.json())
#
#     assert response.status_code == 200
#     data = response.json()
#     assert data["status_code"] == 200
#     assert isinstance(data["data"], list)
#     assert len(data["data"]) == 2


# @pytest.mark.anyio
# async def test_get_user_tasks_internal_error(mocker, async_client: AsyncClient):
#     mocker.patch(
#         "app.services.transaction.project_details_service.database.fetch_all",
#         side_effect=Exception("Internal Error"),
#     )
#     response = await call_get_user_tasks(async_client, 77, 88)
#     assert response.status_code == 500
