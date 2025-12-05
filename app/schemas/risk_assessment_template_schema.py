from typing import Any
from pydantic import BaseModel
from datetime import datetime


class RiskAssessmentTemplateBase(BaseModel):
    risk_assessment_template_name: str


class RiskAssessmentTemplateResponse(BaseModel):
    risk_assessment_template_id: int
    risk_assessment_template_name: str
    risk_assessment_template_json: Any
    created_date: datetime
