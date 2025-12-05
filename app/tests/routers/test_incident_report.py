import pytest
from fastapi import status
from fastapi.encoders import jsonable_encoder
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import json
from app.services.incident_report_service import get_incident_reports


# ------------------------------
# Incident-reports/{user_id}
# ------------------------------

@pytest.mark.anyio
async def test_get_incident_reports_success():
    """
    Test successful retrieval of incident reports
    """
    mock_result = [
        {
            "incident_report_id": 1,
            "project_id": 1,
            "project_phase_id": 1,
            "project_name": "Test Project",
            "phase_name": "Development",
            "raise_comment": "Test comment",
            "raised_date": datetime(2025, 9, 30, tzinfo=timezone.utc),
            "resolve_comment": None,
            "resolved_date": None,
            "is_resolved": False,
        }
    ]

    with patch("app.services.incident_report_service.database") as mock_db:
        with patch("app.services.incident_report_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(return_value=mock_result)

            response = await get_incident_reports(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Incident reports fetched successfully"
            assert data["data"] == jsonable_encoder(mock_result)
            assert len(data["data"]) == 1
            assert data["data"][0]["incident_report_id"] == 1
            assert data["data"][0]["project_id"] == 1
            assert data["data"][0]["project_name"] == "Test Project"
            mock_logger.info.assert_called_with("Fetching incident reports for user_id=1, project_id=1")
            mock_db.fetch_all.assert_called()

@pytest.mark.anyio
async def test_get_incident_reports_no_results():
    """
    Test case where no incident reports are found
    """
    with patch("app.services.incident_report_service.database") as mock_db:
        with patch("app.services.incident_report_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(return_value=[])

            response = await get_incident_reports(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "No incident reports found"
            assert data["data"] == []
            mock_logger.info.assert_called_with("Fetching incident reports for user_id=1, project_id=1")
            mock_db.fetch_all.assert_called()

@pytest.mark.anyio
async def test_get_incident_reports_no_project_id_filter():
    """
    Test retrieval of incident reports without project_id filter
    """
    mock_result = [
        {
            "incident_report_id": 1,
            "project_id": 1,
            "project_phase_id": 1,
            "project_name": "Test Project",
            "phase_name": "Development",
            "raise_comment": "Test comment",
            "raised_date": datetime(2025, 9, 30, tzinfo=timezone.utc),
            "resolve_comment": None,
            "resolved_date": None,
            "is_resolved": False,
        }
    ]

    with patch("app.services.incident_report_service.database") as mock_db:
        with patch("app.services.incident_report_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(return_value=mock_result)

            response = await get_incident_reports(user_id=1, project_id=0)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Incident reports fetched successfully"
            assert data["data"] == jsonable_encoder(mock_result)
            assert len(data["data"]) == 1
            mock_logger.info.assert_called_with("Fetching incident reports for user_id=1, project_id=0")
            mock_db.fetch_all.assert_called()

@pytest.mark.anyio
async def test_get_incident_reports_database_error():
    """
    Test case where an exception occurs during incident reports retrieval
    """
    with patch("app.services.incident_report_service.database") as mock_db:
        with patch("app.services.incident_report_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(side_effect=Exception("Database error"))

            response = await get_incident_reports(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["data"] is None
            mock_logger.exception.assert_called_with("Error fetching incident reports: Database error")
            mock_db.fetch_all.assert_called()

@pytest.mark.anyio
async def test_get_incident_reports_multiple_results():
    """
    Test retrieval of multiple incident reports
    """
    mock_result = [
        {
            "incident_report_id": 1,
            "project_id": 1,
            "project_phase_id": 1,
            "project_name": "Test Project 1",
            "phase_name": "Development",
            "raise_comment": "Test comment 1",
            "raised_date": datetime(2025, 9, 30, tzinfo=timezone.utc),
            "resolve_comment": None,
            "resolved_date": None,
            "is_resolved": False,
        },
        {
            "incident_report_id": 2,
            "project_id": 1,
            "project_phase_id": 1,
            "project_name": "Test Project 1",
            "phase_name": "Development",
            "raise_comment": "Test comment 2",
            "raised_date": datetime(2025, 9, 29, tzinfo=timezone.utc),
            "resolve_comment": "Resolved",
            "resolved_date": datetime(2025, 9, 30, tzinfo=timezone.utc),
            "is_resolved": True,
        }
    ]

    with patch("app.services.incident_report_service.database") as mock_db:
        with patch("app.services.incident_report_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(return_value=mock_result)

            response = await get_incident_reports(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Incident reports fetched successfully"
            assert data["data"] == jsonable_encoder(mock_result)
            assert len(data["data"]) == 2
            assert data["data"][0]["incident_report_id"] == 1
            assert data["data"][1]["incident_report_id"] == 2
            mock_logger.info.assert_called_with("Fetching incident reports for user_id=1, project_id=1")
            mock_db.fetch_all.assert_called()


# @pytest.mark.anyio
# async def test_get_incident_reports_invalid_user_id(async_client):
#     """
#     ✅ Test case with invalid user_id input
#     """
#     response = await async_client.get("/api/incident-reports?user_id=invalid&project_id=1")
#
#     assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
#         f"Expected 422, got {response.status_code}: {response.json()}"
#     )
#     data = response.json()
#     assert data["detail"], "Expected validation error details"
#     assert any(
#         "value is not a valid integer" in str(detail) or "type_error.integer" in str(detail)
#         for detail in data["detail"]
#     ), "Expected integer validation error"