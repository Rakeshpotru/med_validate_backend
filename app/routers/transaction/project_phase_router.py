import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.db.database import database

from app.schemas.transaction.project_phase_schema import MapUsersToPhaseRequest, ProjectPhaseTransferRequest
from app.schemas.transaction.project_schema import ProjectDetailResponse, ProjectCreateRequest,ProjectOut
from app.services.transaction.project_phase_service import map_users_to_project_phase_service, \
    get_users_by_project_phase_id, transfer_project_phase_ownership_service
from app.services.transaction.project_service import get_project_detail, create_project_service,get_all_projects_by_user_id
from fastapi import APIRouter, Depends, UploadFile, File
from typing import List, Optional


router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])
logger = logging.getLogger(__name__)


@router.post("/mapUsersToPhase")
async def map_users_to_phase(payload: MapUsersToPhaseRequest):
    return await map_users_to_project_phase_service(database, payload)

@router.get("/GetUsersByProjectPhaseId/{project_phase_id}")
async def get_users_by_project_phase(project_phase_id: int):
    return await get_users_by_project_phase_id(database, project_phase_id)

@router.post("/TransferProjectPhaseOwnership")
async def transfer_project_phase_ownership(payload: ProjectPhaseTransferRequest):
    return await transfer_project_phase_ownership_service(database, payload)
