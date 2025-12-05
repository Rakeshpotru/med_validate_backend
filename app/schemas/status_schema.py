from pydantic import BaseModel
from typing import Optional

class StatusResponse(BaseModel):
    status_id: int
    status_name: Optional[str]

class StatusCreateRequest(BaseModel):
    status_name: str
    is_active: Optional[bool] = True

class StatusUpdateRequest(BaseModel):
    status_id: Optional[int] = None
    status_name: str

class StatusDeleteRequest(BaseModel):
    status_id: Optional[int] = None
