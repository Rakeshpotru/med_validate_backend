


from fastapi import APIRouter
from app.schemas.risk_assessment_schema import (
    RiskAssessmentCreateRequest,
    RiskAssessmentUpdateRequest,
    RiskAssessmentDeleteRequest
)
from app.services.risk_assessment_service import get_all_risk_assessments, create_risk_assessment, \
    update_risk_assessment, delete_risk_assessment

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllRiskAssessments")
async def get_all():
    return await get_all_risk_assessments()

@router.post("/createRiskAssessment")
async def create(payload: RiskAssessmentCreateRequest):
    return await create_risk_assessment(payload)

@router.put("/updateRiskAssessment")
async def update(payload: RiskAssessmentUpdateRequest):
    return await update_risk_assessment(payload)

@router.delete("/deleteRiskAssessment")
async def delete(payload: RiskAssessmentDeleteRequest):
    return await delete_risk_assessment(payload)
