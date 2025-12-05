from fastapi import APIRouter, Query, Request
from app.schemas.transaction.change_request_schema import ChangeRequestVerifyUpdateRequest
from app.services.transaction.change_request_service import get_unverified_change_requests, get_cr_file_service, \
    update_change_request_verification_status


router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])


@router.get("/getUnverifiedChangeRequests")
async def get_change_requests(request: Request):
    return await get_unverified_change_requests(request)


@router.get("/getChangeRequestFile")
async def get_project_file_api(file_name: str = Query(..., description="Name of the file to retrieve")):
    return await get_cr_file_service(file_name)


@router.post("/updateChangeRequestVerificationStatus")
async def update_change_request_verification(payload: ChangeRequestVerifyUpdateRequest):
    return await update_change_request_verification_status(payload)