from typing import List, Optional
from pydantic import BaseModel

class WorkflowStageCreate(BaseModel):
    work_flow_stage_name: str
    # created_by: int

class WorkflowStageUpdate(BaseModel):
    work_flow_stage_name: Optional[str] = None
    is_active: Optional[bool] = None

class WorkflowStageResponse(BaseModel):
    work_flow_stage_id: int
    work_flow_stage_name: str
    is_active: bool

class WorkflowStageMapPhasesRequest(BaseModel):
    stage_id: int
    phase_ids: List[int]
    user_id: int


class Phase(BaseModel):
    phase_id: int
    phase_name: str

class StagePhaseMapping(BaseModel):
    stage_id: int
    stage_name: str
    phases: List[Phase]