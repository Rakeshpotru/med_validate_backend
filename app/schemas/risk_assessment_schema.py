from pydantic import BaseModel
from typing import Optional

class RiskAssessmentResponse(BaseModel):
    risk_assessment_id: int
    risk_assessment_name: Optional[str]
    risk_assessment_description: str | None = None  # This allows NULL


class RiskAssessmentCreateRequest(BaseModel):
    risk_assessment_name: str
    is_active: Optional[bool] = True

class RiskAssessmentUpdateRequest(BaseModel):
    risk_assessment_id: Optional[int] = None
    risk_assessment_name: str

class RiskAssessmentDeleteRequest(BaseModel):
    risk_assessment_id: Optional[int] = None