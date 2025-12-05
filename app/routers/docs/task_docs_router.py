import logging
from app.db.database import database
from app.schemas.docs.task_docs_schema import SaveProjectTaskDocumentRequest, SubmitProjectTaskDocumentRequest
from app.services.docs.task_docs_service import get_document_by_project_task_id_service, get_phase_documents_by_project_task_id, \
    save_project_task_document_service, submit_project_task_document_service
from fastapi import APIRouter

router = APIRouter(prefix="/docs", tags=["Docs APIs"])
logger = logging.getLogger(__name__)


@router.get("/GetDocumentByProjectTaskId/{project_task_id}")
async def get_document_by_project_task_id(project_task_id: int):
    return await get_document_by_project_task_id_service(database, project_task_id)

@router.post("/saveProjectTaskDocument")
async def save_project_task_document(payload: SaveProjectTaskDocumentRequest):
    return await save_project_task_document_service(database, payload)

@router.post("/submitProjectTaskDocument")
async def submit_project_task_document(payload: SubmitProjectTaskDocumentRequest):
    return await submit_project_task_document_service(database, payload)

@router.get("/GetPhaseDocumentsByProjectTaskId/{project_task_id}")
async def get_document_by_project_task_id(project_task_id: int):
    return await get_phase_documents_by_project_task_id(database, project_task_id)