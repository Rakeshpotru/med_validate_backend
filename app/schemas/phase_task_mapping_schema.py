from typing import List
from pydantic import BaseModel

class SDLC_Task(BaseModel):
    task_id: int
    task_name: str

class SDLC_PhaseWithTasks(BaseModel):
    phase_id: int
    phase_name: str
    tasks: List[SDLC_Task]


class PhaseTaskMappingRequest(BaseModel):
    phase_id: int
    task_ids: List[int]