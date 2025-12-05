from fastapi import APIRouter

from app.schemas.phase_schema import PhaseCreateRequest, PhaseUpdateRequest, PhaseDeleteRequest
from app.services.phase_service import get_all_phases, create_phase, update_phase, delete_phase

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllPhases")
async def get_phases():
    return await get_all_phases()

@router.post("/createPhase")
async def create_phase_api(payload: PhaseCreateRequest):
    return await create_phase(payload)

@router.put("/updatePhase")
async def update_phase_api(payload: PhaseUpdateRequest):
    return await update_phase(payload)

@router.delete("/deletePhase")
async def delete_phase_api(payload: PhaseDeleteRequest):
    return await delete_phase(payload)
