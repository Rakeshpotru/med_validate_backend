from fastapi import APIRouter

from app.schemas.task_schema import TaskCreateRequest, TaskUpdateRequest, TaskDeleteRequest
from app.services.task_service import get_all_tasks, create_task, update_task, delete_task

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllTasks")
async def get_tasks():
    return await get_all_tasks()

@router.post("/createTask")
async def create_task_api(payload: TaskCreateRequest):
    return await create_task(payload)

@router.put("/updateTask")
async def update_task_api(payload: TaskUpdateRequest):
    return await update_task(payload)

@router.delete("/deleteTask")
async def delete_task_api(payload: TaskDeleteRequest):
    return await delete_task(payload)
