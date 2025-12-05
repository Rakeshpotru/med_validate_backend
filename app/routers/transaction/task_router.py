from fastapi import APIRouter, Query
from app.services.transaction.task_service import fetch_tasks_by_user_id, get_all_tasks
from app.db.database import database

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])

@router.get("/GetTasksByUserId/{user_id}")
async def get_tasks_by_user_id(user_id: int):
    return await fetch_tasks_by_user_id(user_id)


@router.get("/getalltasks")
async def get_tasks():
    """
    Get all tasks with assigned users
    """
    return await get_all_tasks()

