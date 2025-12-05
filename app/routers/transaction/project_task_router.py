import logging
from app.db.database import database
from app.schemas.transaction.project_task_schema import MapUsersToTaskRequest
from fastapi import APIRouter
from app.schemas.transaction.task_schema import ProjectTaskTransferRequest
from app.services.transaction.project_task_service import map_users_to_project_task_service, \
    get_users_by_project_task_id, transfer_project_task_ownership_service

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])
logger = logging.getLogger(__name__)


@router.post("/mapUsersToTask")
async def map_users_to_task(payload: MapUsersToTaskRequest):
    return await map_users_to_project_task_service(database, payload)

@router.get("/GetUsersByProjectTaskId/{project_task_id}")
async def get_users_by_project_task(project_task_id: int):
    return await get_users_by_project_task_id(database, project_task_id)

@router.post("/TransferProjectTaskOwnership")
async def transfer_project_task_ownership(payload: ProjectTaskTransferRequest):
    return await transfer_project_task_ownership_service(database, payload)
