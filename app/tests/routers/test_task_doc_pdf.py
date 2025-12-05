from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app  # Your FastAPI main instance

client = TestClient(app)

# Sample DB return structures
MOCK_DOC_1 = {
    "task_doc_id": 1,
    "project_task_id": 10,
    "doc_version": 1,
    "document_json": "<p>Hello World</p>"
}

MOCK_DOC_2 = {
    "task_doc_id": 2,
    "project_task_id": 10,
    "doc_version": 2,
    "document_json": "<p>Hello Universe</p>"
}


#  ---------- Test GET Doc by ID API ----------
@patch("app.services.docs.task_doc_pdf_service.database.fetch_one")
def test_get_doc_success(mock_fetch):
    mock_fetch.return_value = MOCK_DOC_1
    response = client.get("/docs/1")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["data"]["document_json"] == "<p>Hello World</p>"


@patch("app.services.docs.task_doc_pdf_service.database.fetch_one")
def test_get_doc_not_found(mock_fetch):
    mock_fetch.return_value = None
    response = client.get("/docs/99")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 404
    assert data["data"] is None
    assert data["message"] == "Task document not found"


# ---------- Test Compare Docs API ----------
@patch("app.services.docs.task_doc_pdf_service.database.fetch_one")
def test_compare_docs_success(mock_fetch):
    # First call returns current document
    # Second call returns previous version
    mock_fetch.side_effect = [MOCK_DOC_2, MOCK_DOC_1]

    response = client.get("/docs/compare_docs/2")

    assert response.status_code == 200
    assert "<del" in response.text or "<ins" in response.text  #  Markup applied


@patch("app.services.docs.task_doc_pdf_service.database.fetch_one")
def test_compare_docs_only_one_version(mock_fetch):
    mock_fetch.side_effect = [MOCK_DOC_1, None]

    response = client.get("/docs/compare_docs/1")
    assert response.status_code == 200
    assert "<p>Hello World</p>" in response.text  #  Returns same content without diff


@patch("app.services.docs.task_doc_pdf_service.database.fetch_one")
def test_compare_docs_not_found(mock_fetch):
    mock_fetch.return_value = None

    response = client.get("/docs/compare_docs/999")
    data = response.json()

    assert response.status_code == 404
    assert data["message"] == "Task document not found"
