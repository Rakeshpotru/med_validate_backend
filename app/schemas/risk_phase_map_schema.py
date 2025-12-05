from typing import List
from pydantic import BaseModel

class RiskPhaseMappingRequest(BaseModel):
    risk_assessment_id: int
    phase_ids: List[int]
