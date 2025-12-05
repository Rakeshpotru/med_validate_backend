from fastapi import APIRouter

from app.schemas.phase_task_mapping_schema import PhaseTaskMappingRequest
from app.services.phase_task_mapping_service import get_sdlc_phases_with_tasks, map_phase_to_tasks

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getSDLCPhasesWithTasks")
async def get_sdlc_phases_with_tasks_api():
    return await get_sdlc_phases_with_tasks()


@router.post("/mapPhaseToTasks")
async def map_phase_to_tasks_api(payload: PhaseTaskMappingRequest):
    return await map_phase_to_tasks(payload)