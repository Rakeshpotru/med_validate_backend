from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.services.transaction.projects_service import fetch_project_users
from app.schemas.transaction.projects_schema import ProjectUsersResponse

router = APIRouter(prefix="/projects", tags=["Project Users"])

@router.get("/users/{project_id}", response_model=ProjectUsersResponse)
async def get_project_users(project_id: int):
    if project_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid project_id")

    users = await fetch_project_users(project_id)

    return JSONResponse(
        content={
            "status_code": 200,
            "message": "Project users fetched successfully",
            "data":  users
        }
    )