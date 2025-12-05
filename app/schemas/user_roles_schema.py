from pydantic import BaseModel
from typing import Optional

class UserRoleResponse(BaseModel):
    role_id: int
    role_name: Optional[str]

class UserRoleCreateRequest(BaseModel):
    role_name: str
    is_active: Optional[bool] = True

class UserRoleUpdateRequest(BaseModel):
    role_id: int
    role_name: str

class UserRoleDeleteRequest(BaseModel):
    role_id: int
