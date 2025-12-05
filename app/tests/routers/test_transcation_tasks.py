import pytest
import json
from app.services.transaction import task_service


# --- Tests for fetch_tasks_by_user_id ---
@pytest.mark.anyio
async def test_fetch_tasks_by_user_id_success(mocker):
    fake_row = {
        "project_task_id": 1,
        "project_id": 10,
        "project_name": "Demo Project",
        "phase_id": 5,
        "phase_name": "Design",
        "task_name": "Create Wireframes",
        "status_id": 2,
        "submitted": True,
        "created_date": None,
    }
    mocker.patch("app.services.transaction.task_service.database.fetch_all", return_value=[fake_row])

    response = await task_service.fetch_tasks_by_user_id(user_id=1)
    assert response.status_code == 200

    data = json.loads(response.body.decode())
    assert data["status_code"] == 200
    assert data["message"] == "Tasks assigned to user retrieved successfully"
    assert data["data"][0]["task_name"] == "Create Wireframes"


@pytest.mark.anyio
async def test_fetch_tasks_by_user_id_not_found(mocker):
    mocker.patch("app.services.transaction.task_service.database.fetch_all", return_value=[])

    response = await task_service.fetch_tasks_by_user_id(user_id=999)
    assert response.status_code == 404

    data = json.loads(response.body.decode())
    assert data["status_code"] == 404
    assert data["message"] == "No tasks assigned to this user"
    assert data["data"] == []


@pytest.mark.anyio
async def test_fetch_tasks_by_user_id_internal_error(mocker):
    mocker.patch("app.services.transaction.task_service.database.fetch_all", side_effect=Exception("DB crash"))

    response = await task_service.fetch_tasks_by_user_id(user_id=1)
    assert response.status_code == 500

    data = json.loads(response.body.decode())
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []


# --- Tests for get_all_tasks ---
@pytest.mark.anyio
async def test_get_all_tasks_success(mocker):
    fake_row = {
        "project_id": 10,
        "project_name": "Demo Project",
        "phase_id": 5,
        "phase_name": "Design",
        "project_task_id": 1,
        "task_name": "UI Mockups",
        "status_id": 1,
        "created_date": None,
        "users": "alice,bob",
    }
    mocker.patch("app.services.transaction.task_service.database.fetch_all", return_value=[fake_row])

    response = await task_service.get_all_tasks()
    assert response.status_code == 200

    data = json.loads(response.body.decode())
    assert data["status_code"] == 200
    assert data["message"] == "Tasks fetched successfully"
    assert len(data["data"]) == 1
    assert data["data"][0]["phases"][0]["tasks"][0]["task_name"] == "UI Mockups"


@pytest.mark.anyio
async def test_get_all_tasks_not_found(mocker):
    mocker.patch("app.services.transaction.task_service.database.fetch_all", return_value=[])

    response = await task_service.get_all_tasks()
    assert response.status_code == 404

    data = json.loads(response.body.decode())
    assert data["status_code"] == 404
    assert data["message"] == "No tasks found"
    assert data["data"] == []


@pytest.mark.anyio
async def test_get_all_tasks_internal_error(mocker):
    mocker.patch("app.services.transaction.task_service.database.fetch_all", side_effect=Exception("DB fail"))

    response = await task_service.get_all_tasks()
    assert response.status_code == 500

    data = json.loads(response.body.decode())
    assert data["status_code"] == 500
    assert data["message"] == "Internal server error"
    assert data["data"] == []
