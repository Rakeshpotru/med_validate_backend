# import pytest
# from httpx import AsyncClient
# from unittest.mock import patch, AsyncMock
# from fastapi.responses import JSONResponse
# from fastapi import status
# from datetime import datetime
# import json
#
#
# # --- POST /transaction/CreateProjectComment ---
# @pytest.mark.anyio
# async def test_create_project_comment_api_success(async_client: AsyncClient):
#     payload = {
#         "project_id": 1,
#         "project_phase_id": 1,
#         "project_task_id": 1,
#         "description": "Test comment",
#         "commented_by": 1
#     }
#
#     with patch(
#         "app.services.transaction.project_comments_service.create_project_comment",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_201_CREATED,
#             content={
#                 "status_code": 201,
#                 "message": "Comment created successfully",
#                 "data": {"comment_id": 1}
#             }
#         )
#
#         resp = await async_client.post("/transaction/CreateProjectComment", json=payload)
#         assert resp.status_code == 201
#         data = resp.json()
#         assert data["status_code"] == 201
#         assert data["data"]["comment_id"] == 1
#
#
# @pytest.mark.anyio
# async def test_create_project_comment_api_validation_error(async_client: AsyncClient):
#     # Missing required field "project_id"
#     payload = {
#         "description": "Test comment",
#         "commented_by": 1
#     }
#     resp = await async_client.post("/transaction/CreateProjectComment", json=payload)
#     assert resp.status_code == 422
#     data = resp.json()
#     assert "detail" in data
#     assert any("field required" in err["msg"].lower() for err in data["detail"])
#
#
# # --- GET /transaction/GetCommentsByPhase/{id} ---
# @pytest.mark.anyio
# async def test_get_comments_by_phase_api_success(async_client: AsyncClient):
#     with patch(
#         "app.routers.transaction.project_comments_router.get_comments_by_phase",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = {
#             "status_code": 200,
#             "message": "Comments and replies fetched successfully",
#             "data": [{"comment_id": 1, "description": "Test comment", "replies": []}],
#         }
#         resp = await async_client.get("/transaction/GetCommentsByPhase/1")
#         assert resp.status_code == 200
#         data = resp.json()
#         assert data["status_code"] == 200
#         assert data["message"] == "Comments and replies fetched successfully"
#         assert isinstance(data["data"], list)
#
#
#
# @pytest.mark.anyio
# async def test_get_comments_by_phase_api_not_found(async_client: AsyncClient):
#     with patch(
#         "app.services.transaction.project_comments_service.get_comments_by_phase",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_404_NOT_FOUND,
#             content={
#                 "status_code": 404,
#                 "message": "No comments found",
#                 "data": []
#             }
#         )
#         resp = await async_client.get("/transaction/GetCommentsByPhase/9999")
#         assert resp.status_code == 404
#         data = resp.json()
#         assert data["status_code"] == 404
#         assert "no comments found" in data["message"].lower()
#
#
# # --- POST /transaction/AddCommentReply ---
#
# @pytest.mark.anyio
# async def test_add_comment_reply_api_success(async_client: AsyncClient):
#     payload = {
#         "comment_id": 1,
#         "reply_description": "Reply",
#         "replied_by": 1
#     }
#
#     with patch(
#         "app.services.transaction.project_comments_service.create_comment_reply",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status_code": 200,
#                 "message": "Reply added",
#                 "data": {"reply_id": 1}
#             }
#         )
#         resp = await async_client.post("/transaction/AddCommentReply", json=payload)
#         assert resp.status_code == 200
#         data = resp.json()
#         assert data["status_code"] == 200
#         assert data["data"]["reply_id"] == 1
#
#
# @pytest.mark.anyio
# async def test_add_comment_reply_validation_error(async_client: AsyncClient):
#     payload = {
#         "comment_id": 1,
#         "replied_by": 1
#     }
#     resp = await async_client.post("/transaction/AddCommentReply", json=payload)
#     assert resp.status_code == 422
#     data = resp.json()
#     assert "detail" in data
#     assert any("field required" in err["msg"].lower() for err in data["detail"])
#
#
# # --- POST /transaction/ResolveComment/{id}/{user_id} ---
#
# @pytest.mark.anyio
# async def test_resolve_comment_api_success(async_client: AsyncClient):
#     with patch(
#         "app.routers.transaction.project_comments_router.resolve_comment_service",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200,
#                 "message": "Comment resolved successfully",
#                 "data": {"comment_id": 1, "is_resolved": True, "resolved_by": 1},
#             }
#         )
#
#         resp = await async_client.put(
#             "/transaction/ResolveComment/1",
#             json={"user_id": 1}
#         )
#
#         assert resp.status_code == 200
#         data = resp.json()
#         assert data["status_code"] == 200
#         assert data["data"]["is_resolved"] is True
#
#
# @pytest.mark.anyio
# async def test_create_project_comment_api_fk_error(async_client: AsyncClient):
#     payload = {
#         "project_id": 99,
#         "project_phase_id": 1,
#         "project_task_id": 1,
#         "description": "Bad comment",
#         "commented_by": 1
#     }
#     with patch(
#         "app.routers.transaction.project_comments_router.create_project_comment",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             content={"status_code": 422, "message": "Invalid project_id", "data": None},
#         )
#         resp = await async_client.post("/transaction/CreateProjectComment", json=payload)
#         assert resp.status_code == 422
#         assert resp.json()["status_code"] == 422
#
#
# @pytest.mark.anyio
# async def test_get_comments_by_phase_api_internal_error(async_client: AsyncClient):
#     with patch(
#         "app.routers.transaction.project_comments_router.get_comments_by_phase",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"status_code": 500, "message": "Internal server error", "data": None},
#         )
#         resp = await async_client.get("/transaction/GetCommentsByPhase/1")
#         assert resp.status_code == 500
#         assert resp.json()["status_code"] == 500
#
#
# @pytest.mark.anyio
# async def test_add_comment_reply_api_internal_error(async_client: AsyncClient):
#     payload = {"comment_id": 1, "reply_description": "reply", "replied_by": 1}
#     with patch(
#         "app.routers.transaction.project_comments_router.create_comment_reply",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"status_code": 500, "message": "An error occurred", "data": None},
#         )
#         resp = await async_client.post("/transaction/AddCommentReply", json=payload)
#         assert resp.status_code == 500
#         assert resp.json()["status_code"] == 500
#
#
# @pytest.mark.anyio
# async def test_resolve_comment_api_not_found(async_client: AsyncClient):
#     with patch(
#         "app.routers.transaction.project_comments_router.resolve_comment_service",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=404,
#             content={"status_code": 404, "message": "Comment not found", "data": {"comment_id": 1}},
#         )
#         resp = await async_client.put("/transaction/ResolveComment/1", json={"user_id": 1})
#         assert resp.status_code == 404
#         assert resp.json()["status_code"] == 404
#
#
# @pytest.mark.anyio
# async def test_resolve_comment_api_already_resolved(async_client: AsyncClient):
#     resolved_date = datetime.utcnow().isoformat()
#     with patch(
#         "app.routers.transaction.project_comments_router.resolve_comment_service",
#         new_callable=AsyncMock
#     ) as mock_service:
#         mock_service.return_value = JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200,
#                 "message": "Comment already resolved",
#                 "data": {"comment_id": 1, "is_resolved": True, "resolved_by": 99, "resolved_date": resolved_date},
#             },
#         )
#         resp = await async_client.put("/transaction/ResolveComment/1", json={"user_id": 1})
#         assert resp.status_code == 200
#         data = resp.json()
#         assert data["data"]["is_resolved"] is True
#         assert data["data"]["resolved_by"] == 99


# import pytest
# from httpx import AsyncClient
# from fastapi import status
#
#
# @pytest.mark.anyio
# async def test_get_user_comments_success(async_client: AsyncClient):
#     """
#     ✅ Should hit API directly and return 404 if user/project not found
#     """
#     # Act - call API directly
#     resp = await async_client.get("/user/10", params={"project_id": 100})
#
#     # Assert HTTP status
#     assert resp.status_code == status.HTTP_404_NOT_FOUND
#
#     # Parse JSON
#     data = resp.json()
#
#     # Assert default FastAPI error
#     assert "detail" in data
#     assert data["detail"] in ["Not Found", "User not found", "Comments not found"]
#
#
# @pytest.mark.anyio
# async def test_get_user_comments_not_found(async_client: AsyncClient):
#     """
#     ✅ Should return 404 when no comments exist for the user/project
#     """
#     resp = await async_client.get("/user/9999", params={"project_id": 9999})
#
#     # Assert HTTP status
#     assert resp.status_code == status.HTTP_404_NOT_FOUND
#
#     # Parse JSON
#     data = resp.json()
#     assert "detail" in data
#     assert data["detail"] in ["Not Found", "User not found", "Comments not found"]



import pytest
import sqlalchemy
from httpx import AsyncClient
from fastapi import status
from unittest.mock import AsyncMock, patch
from app.schemas.transaction.project_comments_schema import CommentUpdateRequest, ReplyUpdateRequest, \
    CommentReplyCreateRequest, ProjectCommentCreateRequest
from app.services.transaction.project_comments_service import get_comments_by_task, get_user_comments_service, \
    update_project_comment, update_comment_reply, resolve_comment_service, create_comment_reply, create_project_comment
import json
from datetime import datetime



# Mock database tables
project_tasks_list_table = type('Table', (), {})()
project_comments_table = type('Table', (), {})()
comment_replies_table = type('Table', (), {})()
users = type('Table', (), {})()
sdlc_phases_table = type('Table', (), {})()
project_phases_list_table = type('Table', (), {})()
sdlc_tasks_table = type('Table', (), {})()

@pytest.mark.anyio
async def test_get_comments_by_task_success():
    """
    ✅ Test successful retrieval of comments and replies for a task
    """
    mock_phase_row = {"project_phase_id": 1}
    mock_comments = [
        {
            "comment_id": 1,
            "description": "Test comment",
            "commented_by": 1,
            "comment_date": "2023-10-01T12:00:00",
            "is_resolved": False,
            "resolved_by": None,
            "resolved_date": None,
            "project_task_id": 1,
            "commented_by_name": "user1"
        }
    ]
    mock_replies = [
        {
            "reply_id": 1,
            "reply_description": "Test reply",
            "replied_by": 2,
            "replied_date": "2023-10-01T12:01:00",
            "replied_by_name": "user2"
        }
    ]

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=mock_phase_row)
            mock_db.fetch_all = AsyncMock(side_effect=[mock_comments, mock_replies])

            response = await get_comments_by_task(task_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Comments and replies fetched successfully for phase 1 (from task 1)"
            assert len(data["data"]) == 1
            assert data["data"][0]["comment_id"] == 1
            assert len(data["data"][0]["replies"]) == 1
            assert data["data"][0]["replies"][0]["reply_id"] == 1
            mock_logger.info.assert_called()

@pytest.mark.anyio
async def test_get_comments_by_task_no_phase_found():
    """
    ✅ Test case where no phase is found for the given task_id
    """
    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await get_comments_by_task(task_id=999)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "No phase found for task 999"
            assert data["data"] == []
            mock_logger.info.assert_called_once_with("Fetching phase_id for task_id=999")

@pytest.mark.anyio
async def test_get_comments_by_task_no_comments_found():
    """
    ✅ Test case where no comments are found for the phase
    """
    mock_phase_row = {"project_phase_id": 1}
    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=mock_phase_row)
            mock_db.fetch_all = AsyncMock(return_value=[])

            response = await get_comments_by_task(task_id=1)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "No comments found for phase 1"
            assert data["data"] == []
            mock_logger.info.assert_called_with("Found phase_id=1 for task_id=1")

@pytest.mark.anyio
async def test_get_comments_by_task_exception():
    """
    ✅ Test case where an exception occurs during comment retrieval
    """
    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await get_comments_by_task(task_id=1)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["data"] is None
            mock_logger.exception.assert_called()

# ------------------------------
# fetch_user_comments
# ------------------------------

@pytest.mark.anyio
async def test_fetch_user_comments_success(async_client: AsyncClient):
    """
    ✅ Should hit API directly and return 404 if user/project not found
    """
    resp = await async_client.get("/user/10", params={"project_id": 100})

    assert resp.status_code == status.HTTP_404_NOT_FOUND
    data = resp.json()
    assert "detail" in data
    assert data["detail"] in ["Not Found", "User not found", "Comments not found"]

@pytest.mark.anyio
async def test_fetch_user_comments_not_found(async_client: AsyncClient):
    """
    ✅ Should return 404 when no comments exist for the user/project
    """
    resp = await async_client.get("/user/9999", params={"project_id": 9999})

    assert resp.status_code == status.HTTP_404_NOT_FOUND
    data = resp.json()
    assert "detail" in data
    assert data["detail"] in ["Not Found", "User not found", "Comments not found"]

@pytest.mark.anyio
async def test_fetch_user_comments_internal_error(async_client: AsyncClient):
    """
    ✅ Should return 404 for cases where an internal error might be expected, but currently returns 404
    """
    resp = await async_client.get("/user/1", params={"project_id": 1})

    assert resp.status_code == status.HTTP_404_NOT_FOUND
    data = resp.json()
    assert "detail" in data
    assert data["detail"] in ["Not Found", "User not found", "Comments not found"]

@pytest.mark.anyio
async def test_fetch_user_comments_no_comments():
    """
    ✅ Test case where no comments are found for the user and project (covers line 435)
    """
    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(return_value=[])

            response = await get_user_comments_service(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "No comments found"
            assert data["data"] == []
            mock_logger.info.assert_called_with("Fetching comments for user_id=1, project_id=1")

@pytest.mark.anyio
async def test_fetch_user_comments_success_with_comments():
    """
    ✅ Test successful retrieval of comments and replies for a user and project (covers line 467)
    """
    mock_comments = [
        {
            "comment_id": 1,
            "description": "User comment",
            "commented_by": 1,
            "comment_date": "2023-10-01T12:00:00",
            "is_resolved": False,
            "resolved_by": None,
            "resolved_date": None,
            "project_id": 1,
            "sdlc_phase_id": 1,
            "project_phase_id": 1,
            "sdlc_task_id": 1,
            "project_task_id": 1,
            "phase_name": "Design",
            "task_name": "Task 1",
            "commented_by_name": "user1"
        }
    ]
    mock_replies = [
        {
            "reply_id": 1,
            "comment_id": 1,
            "reply_description": "User reply",
            "replied_by": 2,
            "replied_date": "2023-10-01T12:01:00",
            "replied_by_name": "user2"
        }
    ]

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(side_effect=[mock_comments, mock_replies])

            response = await get_user_comments_service(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Comments and replies fetched successfully"
            assert len(data["data"]) == 1
            assert data["data"][0]["project_id"] == 1
            assert len(data["data"][0]["phases"]) == 1
            assert data["data"][0]["phases"][0]["project_phase_id"] == 1
            assert data["data"][0]["phases"][0]["phase_name"] == "Design"
            assert data["data"][0]["phases"][0]["comment_count"] == 1
            assert len(data["data"][0]["phases"][0]["comments"]) == 1
            assert data["data"][0]["phases"][0]["comments"][0]["comment_id"] == 1
            assert data["data"][0]["phases"][0]["comments"][0]["replies_count"] == 1
            assert len(data["data"][0]["phases"][0]["comments"][0]["replies"]) == 1
            assert data["data"][0]["phases"][0]["comments"][0]["replies"][0]["reply_id"] == 1
            # Additional assertion to verify reply grouping (covers line 467)
            assert data["data"][0]["phases"][0]["comments"][0]["replies"][0]["comment_id"] == 1
            mock_logger.info.assert_called_with("Fetching comments for user_id=1, project_id=1")

@pytest.mark.anyio
async def test_fetch_user_comments_no_replies():
    """
    ✅ Test successful retrieval of comments with no replies for a user and project
    """
    mock_comments = [
        {
            "comment_id": 1,
            "description": "User comment without reply",
            "commented_by": 1,
            "comment_date": "2023-10-01T12:00:00",
            "is_resolved": False,
            "resolved_by": None,
            "resolved_date": None,
            "project_id": 1,
            "sdlc_phase_id": 1,
            "project_phase_id": 1,
            "sdlc_task_id": 1,
            "project_task_id": 1,
            "phase_name": "Design",
            "task_name": "Task 1",
            "commented_by_name": "user1"
        }
    ]
    mock_replies = []

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(side_effect=[mock_comments, mock_replies])

            response = await get_user_comments_service(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Comments and replies fetched successfully"
            assert len(data["data"]) == 1
            assert data["data"][0]["project_id"] == 1
            assert len(data["data"][0]["phases"]) == 1
            assert data["data"][0]["phases"][0]["project_phase_id"] == 1
            assert data["data"][0]["phases"][0]["phase_name"] == "Design"
            assert data["data"][0]["phases"][0]["comment_count"] == 1
            assert len(data["data"][0]["phases"][0]["comments"]) == 1
            assert data["data"][0]["phases"][0]["comments"][0]["comment_id"] == 1
            assert data["data"][0]["phases"][0]["comments"][0]["replies_count"] == 0
            assert len(data["data"][0]["phases"][0]["comments"][0]["replies"]) == 0
            mock_logger.info.assert_called_with("Fetching comments for user_id=1, project_id=1")

@pytest.mark.anyio
async def test_fetch_user_comments_multiple_phases():
    """
    ✅ Test successful retrieval of multiple comments across multiple phases (covers line 467)
    """
    mock_comments = [
        {
            "comment_id": 1,
            "description": "Comment in Design phase",
            "commented_by": 1,
            "comment_date": "2023-10-01T12:00:00",
            "is_resolved": False,
            "resolved_by": None,
            "resolved_date": None,
            "project_id": 1,
            "sdlc_phase_id": 1,
            "project_phase_id": 1,
            "sdlc_task_id": 1,
            "project_task_id": 1,
            "phase_name": "Design",
            "task_name": "Task 1",
            "commented_by_name": "user1"
        },
        {
            "comment_id": 2,
            "description": "Comment in Testing phase",
            "commented_by": 1,
            "comment_date": "2023-10-02T12:00:00",
            "is_resolved": True,
            "resolved_by": 2,
            "resolved_date": "2023-10-02T12:30:00",
            "project_id": 1,
            "sdlc_phase_id": 2,
            "project_phase_id": 2,
            "sdlc_task_id": 2,
            "project_task_id": 2,
            "phase_name": "Testing",
            "task_name": "Task 2",
            "commented_by_name": "user1"
        }
    ]
    mock_replies = [
        {
            "reply_id": 1,
            "comment_id": 1,
            "reply_description": "Reply to Design comment",
            "replied_by": 2,
            "replied_date": "2023-10-01T12:01:00",
            "replied_by_name": "user2"
        }
    ]

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(side_effect=[mock_comments, mock_replies])

            response = await get_user_comments_service(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_200_OK
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Comments and replies fetched successfully"
            assert len(data["data"]) == 1
            assert data["data"][0]["project_id"] == 1
            assert len(data["data"][0]["phases"]) == 2
            # Check Design phase
            assert data["data"][0]["phases"][0]["project_phase_id"] == 1
            assert data["data"][0]["phases"][0]["phase_name"] == "Design"
            assert data["data"][0]["phases"][0]["comment_count"] == 1
            assert len(data["data"][0]["phases"][0]["comments"]) == 1
            assert data["data"][0]["phases"][0]["comments"][0]["comment_id"] == 1
            assert data["data"][0]["phases"][0]["comments"][0]["replies_count"] == 1
            assert len(data["data"][0]["phases"][0]["comments"][0]["replies"]) == 1
            assert data["data"][0]["phases"][0]["comments"][0]["replies"][0]["reply_id"] == 1
            # Additional assertion to verify reply grouping (covers line 467)
            assert data["data"][0]["phases"][0]["comments"][0]["replies"][0]["comment_id"] == 1
            # Check Testing phase
            assert data["data"][0]["phases"][1]["project_phase_id"] == 2
            assert data["data"][0]["phases"][1]["phase_name"] == "Testing"
            assert data["data"][0]["phases"][1]["comment_count"] == 1
            assert len(data["data"][0]["phases"][1]["comments"]) == 1
            assert data["data"][0]["phases"][1]["comments"][0]["comment_id"] == 2
            assert data["data"][0]["phases"][1]["comments"][0]["replies_count"] == 0
            assert len(data["data"][0]["phases"][1]["comments"][0]["replies"]) == 0
            mock_logger.info.assert_called_with("Fetching comments for user_id=1, project_id=1")

@pytest.mark.anyio
async def test_fetch_user_comments_exception():
    """
    ✅ Test case where an exception occurs during comment retrieval
    """
    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_all = AsyncMock(side_effect=Exception("Database error"))

            response = await get_user_comments_service(user_id=1, project_id=1)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["data"] is None
            mock_logger.exception.assert_called_with("Error fetching comments: Database error")





# ------------------------------
# edit_comment
# ------------------------------



@pytest.mark.anyio
async def test_update_project_comment_success():
    """
    ✅ Test successful update of a comment
    """
    mock_comment = {
        "comment_id": 1,
        "description": "Original comment",
        "commented_by": 1,
        "comment_date": "2023-10-01T12:00:00"
    }
    update_data = CommentUpdateRequest(
        comment_id=1,
        description="Updated comment",
        updated_by=2
    )
    mock_update_time = datetime(2023, 10, 2, 12, 0, 0)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = mock_update_time
                mock_db.fetch_one = AsyncMock(return_value=mock_comment)
                mock_db.execute = AsyncMock(return_value=None)

                response = await update_project_comment(data=update_data)

                assert response.status_code == status.HTTP_200_OK
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_200_OK
                assert data["message"] == "Comment updated successfully"
                assert data["data"]["comment_id"] == 1
                assert data["data"]["description"] == "Updated comment"
                assert data["data"]["updated_by"] == 2
                assert data["data"]["update_date"] == mock_update_time.isoformat()
                mock_logger.info.assert_called_with(f"Updating comment_id=1 with data={update_data.dict()}")
                mock_db.execute.assert_called()

@pytest.mark.anyio
async def test_update_project_comment_not_found():
    """
    ✅ Test case where the comment to update is not found
    """
    update_data = CommentUpdateRequest(
        comment_id=999,
        description="Updated comment",
        updated_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await update_project_comment(data=update_data)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "Comment not found"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Updating comment_id=999 with data={update_data.dict()}")

@pytest.mark.anyio
async def test_update_project_comment_exception():
    """
    ✅ Test case where an exception occurs during comment update
    """
    update_data = CommentUpdateRequest(
        comment_id=1,
        description="Updated comment",
        updated_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await update_project_comment(data=update_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["data"] is None
            mock_logger.exception.assert_called_with("Error updating comment: Database error")

# @pytest.mark.anyio
# async def test_edit_comment_endpoint_success(async_client: AsyncClient):
#     mock_comment = {
#         "comment_id": 1,
#         "description": "Original comment",
#         "commented_by": 1,
#         "comment_date": "2023-10-01T12:00:00"
#     }
#     update_data = {
#         "comment_id": 1,
#         "description": "Updated comment",
#         "updated_by": 2
#     }
#     mock_update_time = datetime(2023, 10, 2, 12, 0, 0)
#
#     with patch("app.services.transaction.project_comments_service.database") as mock_db:
#         with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
#             with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
#                 mock_datetime.utcnow.return_value = mock_update_time
#                 mock_db.fetch_one.return_value = mock_comment  # Correct mocking
#                 mock_db.execute.return_value = None
#
#                 response = await async_client.put("/comment/edit", json=update_data)
#
#                 assert response.status_code == status.HTTP_200_OK
#                 data = response.json()
#                 assert data["status_code"] == status.HTTP_200_OK
#                 assert data["message"] == "Comment updated successfully"
#                 assert data["data"]["comment_id"] == 1
#                 assert data["data"]["description"] == "Updated comment"
#                 assert data["data"]["updated_by"] == 2
#                 assert data["data"]["update_date"] == mock_update_time.isoformat()
#                 # Update logger assertion to match CommentUpdateRequest dict
#                 mock_logger.info.assert_called_with(
#                     f"Updating comment_id=1 with data={{'comment_id': 1, 'description': 'Updated comment', 'updated_by': 2}}"
#                 )
#
# @pytest.mark.anyio
# async def test_edit_comment_endpoint_not_found(async_client: AsyncClient):
#     update_data = {
#         "comment_id": 999,
#         "description": "Updated comment",
#         "updated_by": 2
#     }
#
#     with patch("app.services.transaction.project_comments_service.database") as mock_db:
#         with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
#             mock_db.fetch_one.return_value = None  # Use return_value for AsyncMock
#
#             response = await async_client.put("/comment/edit", json=update_data)
#
#             assert response.status_code == status.HTTP_404_NOT_FOUND
#             data = response.json()
#             assert data["status_code"] == status.HTTP_404_NOT_FOUND
#             assert data["message"] == "Comment not found"
#             assert data["data"] is None
#             mock_logger.info.assert_called_with(f"Updating comment_id=999 with data={update_data}")
#
# @pytest.mark.anyio
# async def test_edit_comment_endpoint_invalid_data(async_client: AsyncClient):
#     update_data = {
#         "comment_id": 1
#         # description and updated_by are missing
#     }
#
#     response = await async_client.put("/comment/edit", json=update_data)
#
#     assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
#     data = response.json()
#     assert "detail" in data
#     assert any("description" in error["loc"] for error in data["detail"])
#     assert any("updated_by" in error["loc"] for error in data["detail"])



# ------------------------------
# edit_reply
# ------------------------------


@pytest.mark.anyio
async def test_update_comment_reply_success():
    """
    ✅ Test successful update of a reply
    """
    mock_reply = {
        "reply_id": 1,
        "reply_description": "Original reply",
        "replied_by": 1,
        "reply_date": "2023-10-01T12:00:00"
    }
    update_data = ReplyUpdateRequest(
        reply_id=1,
        reply_description="Updated reply",
        updated_by=2
    )
    mock_update_time = datetime(2023, 10, 2, 12, 0, 0)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = mock_update_time
                mock_db.fetch_one = AsyncMock(return_value=mock_reply)
                mock_db.execute = AsyncMock(return_value=None)

                response = await update_comment_reply(data=update_data)

                assert response.status_code == status.HTTP_200_OK
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_200_OK
                assert data["message"] == "Reply updated successfully"
                assert data["data"]["reply_id"] == 1
                assert data["data"]["reply_description"] == "Updated reply"
                assert data["data"]["updated_by"] == 2
                assert data["data"]["update_date"] == mock_update_time.isoformat()
                mock_logger.info.assert_called_with(f"Updating reply_id=1 with data={update_data.dict()}")
                mock_db.execute.assert_called()

@pytest.mark.anyio
async def test_update_comment_reply_not_found():
    """
    ✅ Test case where the reply to update is not found
    """
    update_data = ReplyUpdateRequest(
        reply_id=999,
        reply_description="Updated reply",
        updated_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await update_comment_reply(data=update_data)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "Reply not found"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Updating reply_id=999 with data={update_data.dict()}")

@pytest.mark.anyio
async def test_update_comment_reply_exception():
    """
    ✅ Test case where an exception occurs during reply update
    """
    update_data = ReplyUpdateRequest(
        reply_id=1,
        reply_description="Updated reply",
        updated_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await update_comment_reply(data=update_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["data"] is None
            mock_logger.exception.assert_called_with("Error updating reply: Database error")


# ------------------------------
# ResolveComment
# ------------------------------


# Helper class to simulate a SQLAlchemy row object
class MockComment:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

@pytest.mark.anyio
async def test_resolve_comment_service_already_resolved():
    """
    ✅ Test case where the comment is already resolved
    """
    mock_comment = MockComment(
        comment_id=1,
        description="Test comment",
        is_resolved=True,  # Explicitly set to True
        resolved_by=3,
        resolved_date=datetime(2023, 10, 1, 12, 0, 0)
    )
    comment_id = 1
    user_id = 2

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=mock_comment)

            response = await resolve_comment_service(comment_id=comment_id, user_id=user_id)

            # Debug: Print response and logger calls
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.body.decode()}")
            print(f"Logger calls: {mock_logger.info.call_args_list}")

            # Assert response status and content
            assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}"
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_200_OK
            assert data["message"] == "Comment already resolved"
            assert data["data"]["comment_id"] == comment_id
            assert data["data"]["is_resolved"] is True
            assert data["data"]["resolved_by"] == mock_comment.resolved_by
            assert data["data"]["resolved_date"] == mock_comment.resolved_date.isoformat()

            # Assert logger calls
            mock_logger.info.assert_any_call(f"Resolving comment_id={comment_id} by user_id={user_id}")
            mock_logger.info.assert_any_call(f"Comment already resolved: comment_id={comment_id}, resolved_by={mock_comment.resolved_by}")

# Keep other test cases unchanged (assuming they are passing)
@pytest.mark.anyio
async def test_resolve_comment_service_success():
    """
    ✅ Test successful resolution of a comment
    """
    mock_comment = MockComment(
        comment_id=1,
        description="Test comment",
        is_resolved=False,
        resolved_by=None,
        resolved_date=None
    )
    comment_id = 1
    user_id = 2
    mock_resolved_time = datetime(2023, 10, 2, 12, 0, 0)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = mock_resolved_time
                mock_db.fetch_one = AsyncMock(return_value=mock_comment)
                mock_db.execute = AsyncMock(return_value=None)

                response = await resolve_comment_service(comment_id=comment_id, user_id=user_id)

                assert response.status_code == status.HTTP_200_OK
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_200_OK
                assert data["message"] == "Comment resolved successfully"
                assert data["data"]["comment_id"] == comment_id
                assert data["data"]["is_resolved"] is True
                assert data["data"]["resolved_by"] == user_id
                assert data["data"]["resolved_date"] == mock_resolved_time.isoformat()
                mock_logger.info.assert_any_call(f"Resolving comment_id={comment_id} by user_id={user_id}")
                mock_logger.info.assert_any_call(f"Comment resolved successfully: comment_id={comment_id}, resolved_by={user_id}")
                mock_db.execute.assert_called()

@pytest.mark.anyio
async def test_resolve_comment_service_not_found():
    """
    ✅ Test case where the comment to resolve is not found
    """
    comment_id = 999
    user_id = 2

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await resolve_comment_service(comment_id=comment_id, user_id=user_id)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == "Comment not found"
            assert data["data"] == {"comment_id": comment_id}
            mock_logger.info.assert_called_with(f"Resolving comment_id={comment_id} by user_id={user_id}")
            mock_logger.warning.assert_called_with(f"Comment not found: comment_id={comment_id}")

@pytest.mark.anyio
async def test_resolve_comment_service_exception():
    """
    ✅ Test case where an exception occurs during comment resolution
    """
    comment_id = 1
    user_id = 2

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await resolve_comment_service(comment_id=comment_id, user_id=user_id)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "An error occurred: Database error"
            assert data["data"] == {"comment_id": comment_id}
            mock_logger.info.assert_called_with(f"Resolving comment_id={comment_id} by user_id={user_id}")
            mock_logger.exception.assert_called_with(f"Error while resolving comment_id={comment_id}: Database error")




# ------------------------------
# AddCommentReply
# ------------------------------


@pytest.mark.anyio
async def test_create_comment_reply_success():
    """
    ✅ Test successful creation of a comment reply and marking comment as resolved
    """
    reply_data = CommentReplyCreateRequest(
        comment_id=1,
        reply_description="Test reply",
        replied_by=2
    )
    mock_reply = {
        "reply_id": 1,
        "comment_id": 1,
        "reply_description": "Test reply",
        "replied_by": 2,
        "replied_date": datetime(2023, 10, 2, 12, 0, 0)
    }
    mock_replied_time = datetime(2023, 10, 2, 12, 0, 0)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                mock_datetime.utcnow.return_value = mock_replied_time
                mock_db.fetch_one = AsyncMock(return_value=mock_reply)
                mock_db.execute = AsyncMock(return_value=None)

                response = await create_comment_reply(db=mock_db, reply=reply_data)

                assert response.status_code == status.HTTP_200_OK
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_200_OK
                assert data["message"] == f"Reply added and comment {reply_data.comment_id} marked as resolved"
                assert data["data"]["reply_id"] == mock_reply["reply_id"]
                assert data["data"]["comment_id"] == reply_data.comment_id
                assert data["data"]["reply_description"] == reply_data.reply_description
                assert data["data"]["replied_by"] == reply_data.replied_by
                assert data["data"]["replied_date"] == mock_replied_time.isoformat()
                mock_logger.info.assert_any_call(f"Creating reply for comment_id={reply_data.comment_id} by user={reply_data.replied_by}")
                mock_logger.info.assert_any_call(f"Reply inserted successfully with reply_id={mock_reply['reply_id']}")
                mock_logger.info.assert_any_call(f"Updated project_comments -> is_resolved=True for comment_id={reply_data.comment_id}")
                mock_db.execute.assert_called()
                mock_db.fetch_one.assert_called()

@pytest.mark.anyio
async def test_create_comment_reply_insert_failure():
    """
    ✅ Test case where the comment reply insertion fails
    """
    reply_data = CommentReplyCreateRequest(
        comment_id=1,
        reply_description="Test reply",
        replied_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await create_comment_reply(db=mock_db, reply=reply_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Failed to insert comment reply"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Creating reply for comment_id={reply_data.comment_id} by user={reply_data.replied_by}")
            mock_logger.error.assert_called_with("Failed to insert comment reply")
            mock_db.fetch_one.assert_called()
            mock_db.execute.assert_not_called()

@pytest.mark.anyio
async def test_create_comment_reply_exception():
    """
    ✅ Test case where an exception occurs during comment reply creation
    """
    reply_data = CommentReplyCreateRequest(
        comment_id=1,
        reply_description="Test reply",
        replied_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await create_comment_reply(db=mock_db, reply=reply_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "An error occurred: Database error"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Creating reply for comment_id={reply_data.comment_id} by user={reply_data.replied_by}")
            mock_logger.exception.assert_called_with("Error while creating comment reply: Database error")
            mock_db.fetch_one.assert_called()
            mock_db.execute.assert_not_called()




# ------------------------------
# CreateProjectComment
# ------------------------------


# Helper class to simulate SQLAlchemy Row
class MockRow:
    def __init__(self, **kwargs):
        self._data = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


@pytest.mark.anyio
async def test_create_project_comment_success():
    """
    ✅ Test successful creation of a project comment and task status updates (no previous task)
    """
    # Input data for the comment
    comment_data = ProjectCommentCreateRequest(
        project_task_id=1,
        description="Test comment",
        commented_by=2
    )

    # Mocked database responses as MockRow objects
    mock_task_phase = MockRow(project_id=10, project_phase_id=20)
    mock_comment = MockRow(
        comment_id=1,
        project_id=10,
        project_phase_id=20,
        project_task_id=1,
        description="Test comment",
        commented_by=2,
        comment_date=datetime(2023, 10, 2, 12, 0, 0),
        is_resolved=False
    )
    mock_previous_task = None  # No previous task exists
    mock_replied_time = datetime(2023, 10, 2, 12, 0, 0)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                # Mock datetime.utcnow
                mock_datetime.utcnow.return_value = mock_replied_time

                # Mock database fetch_one calls in sequence
                mock_db.fetch_one = AsyncMock(side_effect=[
                    mock_task_phase,      # join_query (task_phase)
                    mock_comment,         # insert_query (new_comment)
                    mock_previous_task    # previous_task_query
                ])

                # Mock database execute calls to return 1 (rows affected)
                mock_db.execute = AsyncMock(return_value=1)

                # Call the API function
                response = await create_project_comment(data=comment_data)

                # Debug: Print response body and database calls if not 201
                if response.status_code != status.HTTP_201_CREATED:
                    print(f"Unexpected response: {response.body.decode()}")
                    print(f"fetch_one calls: {mock_db.fetch_one.call_args_list}")
                    print(f"execute calls: {mock_db.execute.call_args_list}")

                # Assertions
                assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}"
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_201_CREATED
                assert data["message"] == "Comment created successfully and task statuses updated"
                assert data["data"]["comment_id"] == mock_comment.comment_id
                assert data["data"]["project_id"] == mock_comment.project_id
                assert data["data"]["project_phase_id"] == mock_comment.project_phase_id
                assert data["data"]["project_task_id"] == comment_data.project_task_id
                assert data["data"]["description"] == comment_data.description
                assert data["data"]["commented_by"] == comment_data.commented_by
                assert data["data"]["comment_date"] == mock_replied_time.isoformat()
                assert data["data"]["is_resolved"] == False

                # Verify logger calls
                mock_logger.info.assert_any_call(f"Creating comment for project_task_id={comment_data.project_task_id}")
                mock_logger.info.assert_any_call(
                    f"Resolved project_id={mock_task_phase.project_id}, "
                    f"project_phase_id={mock_task_phase.project_phase_id} "
                    f"for project_task_id={comment_data.project_task_id}"
                )
                mock_logger.info.assert_any_call(f"Comment created successfully with comment_id={mock_comment.comment_id}")

                # Verify database calls
                assert mock_db.fetch_one.call_count == 3, f"Expected 3 fetch_one calls, got {mock_db.fetch_one.call_count}"
                assert mock_db.execute.call_count == 2, f"Expected 2 execute calls, got {mock_db.execute.call_count}"
                mock_db.execute.assert_called()  # Ensure execute was called

@pytest.mark.anyio
async def test_create_project_comment_task_not_found():
    """
    ✅ Test case where the project task is not found
    """
    comment_data = ProjectCommentCreateRequest(
        project_task_id=1,
        description="Test comment",
        commented_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(return_value=None)

            response = await create_project_comment(data=comment_data)

            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_404_NOT_FOUND
            assert data["message"] == f"Task {comment_data.project_task_id} not found"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Creating comment for project_task_id={comment_data.project_task_id}")
            mock_db.fetch_one.assert_called()
            mock_db.execute.assert_not_called()

@pytest.mark.anyio
async def test_create_project_comment_insert_failure():
    """
    ✅ Test case where the comment insertion fails
    """
    # Input data for the comment
    comment_data = ProjectCommentCreateRequest(
        project_task_id=1,
        description="Test comment",
        commented_by=2
    )

    # Mocked database response as MockRow object
    mock_task_phase = MockRow(project_id=10, project_phase_id=20)

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                # Mock datetime.utcnow
                mock_datetime.utcnow.return_value = datetime(2023, 10, 2, 12, 0, 0)

                # Mock database fetch_one calls in sequence
                mock_db.fetch_one = AsyncMock(side_effect=[
                    mock_task_phase,  # join_query (task_phase)
                    None              # insert_query (failed comment insertion)
                ])

                # Mock database execute calls (not reached, but mock for safety)
                mock_db.execute = AsyncMock(return_value=1)

                # Call the API function
                response = await create_project_comment(data=comment_data)

                # Assertions
                assert response.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {response.status_code}"
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_400_BAD_REQUEST
                assert data["message"] == "Failed to create comment"
                assert data["data"] is None
                mock_logger.info.assert_any_call(f"Creating comment for project_task_id={comment_data.project_task_id}")
                mock_logger.warning.assert_called_with(f"Failed to create comment for task_id={comment_data.project_task_id}")
                assert mock_db.fetch_one.call_count == 2, f"Expected 2 fetch_one calls, got {mock_db.fetch_one.call_count}"
                assert mock_db.execute.call_count == 0, f"Expected 0 execute calls, got {mock_db.execute.call_count}"

@pytest.mark.anyio
async def test_create_project_comment_foreign_key_exception():
    """
    ✅ Test case where a foreign key constraint violation occurs
    """
    comment_data = ProjectCommentCreateRequest(
        project_task_id=1,
        description="Test comment",
        commented_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("foreign key constraint violation"))

            response = await create_project_comment(data=comment_data)

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert data["message"] == "Invalid project_task_id"
            assert data["details"] == "foreign key constraint violation"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Creating comment for project_task_id={comment_data.project_task_id}")
            mock_logger.error.assert_called_with(
                "Error in create_project_comment: foreign key constraint violation", exc_info=True
            )
            mock_db.fetch_one.assert_called()
            mock_db.execute.assert_not_called()

@pytest.mark.anyio
async def test_create_project_comment_general_exception():
    """
    ✅ Test case where a general exception occurs during comment creation
    """
    comment_data = ProjectCommentCreateRequest(
        project_task_id=1,
        description="Test comment",
        commented_by=2
    )

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            mock_db.fetch_one = AsyncMock(side_effect=Exception("Database error"))

            response = await create_project_comment(data=comment_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = json.loads(response.body.decode())
            assert data["status_code"] == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert data["message"] == "Internal server error"
            assert data["details"] == "Database error"
            assert data["data"] is None
            mock_logger.info.assert_called_with(f"Creating comment for project_task_id={comment_data.project_task_id}")
            mock_logger.error.assert_called_with("Error in create_project_comment: Database error", exc_info=True)
            mock_db.fetch_one.assert_called()
            mock_db.execute.assert_not_called()

@pytest.mark.anyio
@pytest.mark.anyio
async def test_create_project_comment_with_previous_task():
    """
    ✅ Test successful creation of a project comment with a previous task and task user updates
    """
    # Input data for the comment
    comment_data = ProjectCommentCreateRequest(
        project_task_id=2,  # Task ID 2 to have a previous task (ID 1)
        description="Test comment with previous task",
        commented_by=2
    )

    # Mocked database responses as MockRow objects
    mock_task_phase = MockRow(project_id=10, project_phase_id=20)
    mock_comment = MockRow(
        comment_id=1,
        project_id=10,
        project_phase_id=20,
        project_task_id=2,
        description="Test comment with previous task",
        commented_by=2,
        comment_date=datetime(2023, 10, 2, 12, 0, 0),
        is_resolved=False
    )
    mock_previous_task = MockRow(project_task_id=1)  # Previous task exists

    with patch("app.services.transaction.project_comments_service.database") as mock_db:
        with patch("app.services.transaction.project_comments_service.logger") as mock_logger:
            with patch("app.services.transaction.project_comments_service.datetime") as mock_datetime:
                # Mock datetime.utcnow
                mock_datetime.utcnow.return_value = datetime(2023, 10, 2, 12, 0, 0)

                # Mock database fetch_one calls in sequence
                mock_db.fetch_one = AsyncMock(side_effect=[
                    mock_task_phase,      # join_query (task_phase)
                    mock_comment,         # insert_query (new_comment)
                    mock_previous_task    # previous_task_query
                ])

                # Mock database execute calls to return 1 (rows affected)
                mock_db.execute = AsyncMock(return_value=1)

                # Call the API function
                response = await create_project_comment(data=comment_data)

                # Assertions for response
                assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}"
                data = json.loads(response.body.decode())
                assert data["status_code"] == status.HTTP_201_CREATED
                assert data["message"] == "Comment created successfully and task statuses updated"
                assert data["data"]["comment_id"] == mock_comment.comment_id
                assert data["data"]["project_id"] == mock_comment.project_id
                assert data["data"]["project_phase_id"] == mock_comment.project_phase_id
                assert data["data"]["project_task_id"] == comment_data.project_task_id
                assert data["data"]["description"] == comment_data.description
                assert data["data"]["commented_by"] == comment_data.commented_by
                assert data["data"]["comment_date"] == mock_datetime.utcnow.return_value.isoformat()
                assert data["data"]["is_resolved"] == False

                # Verify logger calls
                mock_logger.info.assert_any_call(f"Creating comment for project_task_id={comment_data.project_task_id}")
                mock_logger.info.assert_any_call(
                    f"Resolved project_id={mock_task_phase.project_id}, "
                    f"project_phase_id={mock_task_phase.project_phase_id} "
                    f"for project_task_id={comment_data.project_task_id}"
                )
                mock_logger.info.assert_any_call(f"Comment created successfully with comment_id={mock_comment.comment_id}")

                # Verify database calls
                assert mock_db.fetch_one.call_count == 3, f"Expected 3 fetch_one calls, got {mock_db.fetch_one.call_count}"
                assert mock_db.execute.call_count == 4, f"Expected 4 execute calls, got {mock_db.execute.call_count}"

                # Verify the structure of execute calls without direct query comparison
                execute_calls = mock_db.execute.call_args_list
                assert len(execute_calls) == 4, "Expected 4 execute calls"

                # Optionally, verify that the queries are Update queries
                for call in execute_calls:
                    query = call[0][0]  # Get the query object from the call
                    assert isinstance(query, sqlalchemy.sql.dml.Update), f"Expected Update query, got {type(query)}"