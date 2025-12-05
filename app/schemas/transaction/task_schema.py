from datetime import datetime

from pydantic import BaseModel
from typing import Optional, List

class UserTaskResponse(BaseModel):
    project_id: int
    project_name: str
    phase_id: int
    phase_name: str
    project_task_id: int
    task_name: str
    status_id: Optional[int]
    equipment_id: Optional[int]=None
    submitted: bool

class APIResponse(BaseModel):
    status: str
    status_code: int
    message: str
    data: List[UserTaskResponse]



class Role(BaseModel):
    role_id: int
    role_name: str

class UserResponse(BaseModel):
    user_id: int
    user_name: str
    email: str
    roles: List[Role]

class AllTaskResponse(BaseModel):
    project_id: int
    project_name: str
    phase_id: int
    phase_name: str
    project_task_id: int
    task_name: str
    status_id: int
    created_date: Optional[str]
    equipment_id: int
    users: Optional[str]

class UserResponseByTask(BaseModel):
    user_id: int
    user_name: str
    email: str

class ProjectTaskTransferRequest(BaseModel):
    project_task_id: int
    from_user_id: int
    to_user_id: int
    task_transfer_reason: str