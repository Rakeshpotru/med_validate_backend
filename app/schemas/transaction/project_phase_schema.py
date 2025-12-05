from typing import List, Optional
from pydantic import BaseModel

class MapUsersToPhaseRequest(BaseModel):
    project_phase_id: int
    user_ids: List[int]
    # previous_user_id: Optional[int] = None
    # user_transfer_reason: Optional[str] = None

class UserResponseByProject(BaseModel):
    user_id: int
    user_name: str
    email: str
    image_url: Optional[str] = None

class ProjectPhaseTransferRequest(BaseModel):
    project_phase_id: int
    from_user_id: int
    to_user_id: int
    phase_transfer_reason: str