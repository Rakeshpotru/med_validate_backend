from pydantic import BaseModel
from typing import Optional

class TaskResponse(BaseModel):
    task_id: int
    task_name: Optional[str]
    order_id: Optional[int] = None

class TaskCreateRequest(BaseModel):
    task_name: str
    order_id: int
    is_active: Optional[bool] = True

class TaskUpdateRequest(BaseModel):
    task_id: int
    task_name: str
    order_id: int

class TaskDeleteRequest(BaseModel):
    task_id: int
