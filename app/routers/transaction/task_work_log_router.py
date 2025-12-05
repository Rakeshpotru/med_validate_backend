from fastapi import APIRouter, Query
from app.schemas.transaction.task_work_log_schema import TaskWorkLogCreateRequest, UpdateProjectTaskStatusRequest
from app.services.transaction.task_work_log_service import get_task_work_log_details_by_project_task_id, \
    create_task_work_log, update_project_task_status

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])

@router.get("/getTaskWorkLogDetailsByProjectTaskId")
async def get_task_work_log_details(project_task_id: int = Query(..., description="Project Task ID")):
    return await get_task_work_log_details_by_project_task_id(project_task_id)


@router.post("/createTaskWorkLog")
async def create_task_work_log_api(payload: TaskWorkLogCreateRequest):
    return await create_task_work_log(payload)

@router.post("/updateProjectTaskStatusForTaskWorkLog")
async def update_project_task_status_api(request: UpdateProjectTaskStatusRequest):
    return await update_project_task_status(
        project_task_id=request.project_task_id,
        task_status_id=request.task_status_id
    )