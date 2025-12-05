import logging
from app.services.transaction.project_details_service import get_project_details_by_id, get_projects_by_user_service, \
    get_user_tasks_service, get_project_file_service
from fastapi import APIRouter, Query
from app.db.database import database


router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])
logger = logging.getLogger(__name__)


@router.get("/new_getProjectsByUser/{user_id}")
async def get_projects_by_user(user_id: int):
    return await get_projects_by_user_service(database, user_id)


@router.get("/new_getProjectDetails/{project_id}")
async def get_project_details(project_id: int):
    return await get_project_details_by_id(project_id)


@router.get("/new_getUserTasks")
async def get_user_tasks(
    user_id: int = Query(..., description="User ID"),
    project_id: int = Query(0, description="Project ID (0 to fetch all projects)")
):
    return await get_user_tasks_service(database, user_id, project_id)


@router.get("/getProjectFile")
async def get_project_file_api(file_name: str = Query(..., description="Name of the file to retrieve")):
    return await get_project_file_service(file_name)