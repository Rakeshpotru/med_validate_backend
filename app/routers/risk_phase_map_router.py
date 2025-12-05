from fastapi import APIRouter

from app.schemas.risk_phase_map_schema import RiskPhaseMappingRequest
from app.services.risk_phase_map_service import map_risk_to_phases, get_all_risks_with_phases_only_from_mapping

router = APIRouter(prefix="/master", tags=["Master APIs"])


@router.post("/mapRiskToPhases")
async def map_risk_to_phases_api(payload: RiskPhaseMappingRequest):
    return await map_risk_to_phases(payload)


@router.get("/getAllMappedRisksWithPhases")
async def get_all_mapped_risks_with_phases_api():
    return await get_all_risks_with_phases_only_from_mapping()
