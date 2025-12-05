from fastapi import APIRouter

from app.schemas.status_schema import StatusCreateRequest, StatusUpdateRequest, StatusDeleteRequest
from app.services.status_service import get_all_status, create_status, update_status, delete_status

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllStatus")
async def get_status():
    return await get_all_status()

@router.post("/createStatus")
async def create_status_api(payload: StatusCreateRequest):
    return await create_status(payload)

@router.put("/updateStatus")
async def update_status_api(payload: StatusUpdateRequest):
    return await update_status(payload)

@router.delete("/deleteStatus")
async def delete_status_api(payload: StatusDeleteRequest):
    return await delete_status(payload)
