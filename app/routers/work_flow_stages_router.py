import logging
from typing import List
from fastapi import APIRouter
from app.db.database import database

from app.schemas.work_flow_stages_schema import (
    StagePhaseMapping, WorkflowStageCreate, WorkflowStageUpdate, WorkflowStageMapPhasesRequest
)
from app.services.work_flow_stages_service import (
    create_workflow_stage_service,
    get_stage_phase_mapping_service,
    update_workflow_stage_service,
    delete_workflow_stage_service,
    get_all_workflow_stages_service,
    map_phases_to_stage_service,
    get_phases_by_stage_service
)

router = APIRouter(prefix="/master", tags=["Master APIs"])
logger = logging.getLogger(__name__)


@router.post("/addWorkFlowStage")
async def create_stage(payload: WorkflowStageCreate):
    return await create_workflow_stage_service(database, payload)


@router.put("/updateWorkFlowStage/{stage_id}")
async def update_stage(stage_id: int, payload: WorkflowStageUpdate):
    return await update_workflow_stage_service(database, stage_id, payload)


@router.delete("/deleteWorkFlowStage/{stage_id}")
async def delete_stage(stage_id: int):
    return await delete_workflow_stage_service(database, stage_id)


@router.get("/getAllstages")
async def get_stages():
    return await get_all_workflow_stages_service(database)


@router.post("/map-phases")
async def map_phases(payload: WorkflowStageMapPhasesRequest):
    return await map_phases_to_stage_service(database, payload)


# @router.get("/workFlowStage/{stage_id}/phases")
# async def get_stage_phases(stage_id: int):
#     return await get_phases_by_stage_service(database, stage_id)


@router.get("/GetworkFlowStagePhaseMapping", response_model=List[StagePhaseMapping])
async def get_stage_phase_mapping():
    data = await get_stage_phase_mapping_service()
    return data