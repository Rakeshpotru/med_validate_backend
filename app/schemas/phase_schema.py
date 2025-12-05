from pydantic import BaseModel
from typing import Optional

class PhaseResponse(BaseModel):
    phase_id: int
    phase_name: Optional[str]
    order_id: Optional[int] = None

class PhaseCreateRequest(BaseModel):
    phase_name: str
    order_id:int
    is_active: Optional[bool] = True

class PhaseUpdateRequest(BaseModel):
    phase_id: int
    phase_name: str
    order_id: int

class PhaseDeleteRequest(BaseModel):
    phase_id: int
