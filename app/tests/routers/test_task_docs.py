import pytest
from httpx import AsyncClient
from app.db.database import database
from app.db.docs.task_docs import task_docs_table
from app.schemas.docs.task_docs_schema import SaveProjectTaskDocumentRequest, SubmitProjectTaskDocumentRequest
from datetime import datetime

@pytest.mark.anyio
async def test_get_document_by_project_task_id_missing(async_client: AsyncClient):
    response = await async_client.get("/docs/GetDocumentByProjectTaskId/0")
    assert response.status_code == 400
    data = response.json()
    assert data["status_code"] == 400
    assert "project_task_id is required" in data["message"]

@pytest.mark.anyio
async def test_get_document_by_project_task_id_task_doc_found(async_client: AsyncClient):
    # Insert dummy task_doc
    task_doc_id = await database.execute(
        task_docs_table.insert().values(
            project_task_id=1,
            document_json='{"dummy":"data"}',
            is_latest=True,
            created_by=1,
            created_date=datetime.utcnow(),
            doc_version=1
        )
    )
    response = await async_client.get("/docs/GetDocumentByProjectTaskId/1")
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["data"]["file_flag"] == 2
    assert data["data"]["task_document"] == '{"dummy":"data"}'

@pytest.mark.anyio
async def test_save_project_task_document_create(async_client: AsyncClient):
    payload = SaveProjectTaskDocumentRequest(
        project_task_id=2,
        document_json='{"new":"doc"}',
        created_by=1
    )
    response = await async_client.post("/docs/saveProjectTaskDocument", json=payload.dict())
    assert response.status_code == 201
    data = response.json()
    assert data["status_code"] == 201
    assert "task_doc_id" in data["data"]

@pytest.mark.anyio
async def test_save_project_task_document_update(async_client: AsyncClient):
    # Create existing doc
    task_doc_id = await database.execute(
        task_docs_table.insert().values(
            project_task_id=3,
            document_json='{"old":"doc"}',
            is_latest=True,
            created_by=1,
            created_date=datetime.utcnow(),
            doc_version=1
        )
    )
    payload = SaveProjectTaskDocumentRequest(
        project_task_id=3,
        document_json='{"updated":"doc"}',
        created_by=1
    )
    response = await async_client.post("/docs/saveProjectTaskDocument", json=payload.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["status_code"] == 200
    assert data["message"] == "Document updated successfully"

@pytest.mark.anyio
async def test_submit_project_task_document_first_version(async_client: AsyncClient):
    payload = SubmitProjectTaskDocumentRequest(
        project_task_id=4,
        document_json='{"first":"version"}',
        created_by=1
    )
    response = await async_client.post("/docs/submitProjectTaskDocument", json=payload.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["doc_version"] == 1

@pytest.mark.anyio
async def test_submit_project_task_document_new_version(async_client: AsyncClient):
    # Insert existing doc version
    await database.execute(
        task_docs_table.insert().values(
            project_task_id=5,
            document_json='{"old":"doc"}',
            is_latest=True,
            created_by=1,
            created_date=datetime.utcnow(),
            doc_version=1
        )
    )
    payload = SubmitProjectTaskDocumentRequest(
        project_task_id=5,
        document_json='{"new":"doc"}',
        created_by=1
    )
    response = await async_client.post("/docs/submitProjectTaskDocument", json=payload.dict())
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["doc_version"] == 2
