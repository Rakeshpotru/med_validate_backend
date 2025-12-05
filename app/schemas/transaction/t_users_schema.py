from pydantic import BaseModel,EmailStr
from typing import Optional
from datetime import datetime





class UserUpdateRequest(BaseModel):
    user_id: int
    user_name: str
    email: EmailStr
    is_active: Optional[bool] = True
    updated_by: Optional[int]

class UserDeleteRequest(BaseModel):
    user_id: int
    updated_by: Optional[int]


class CreateUserRequest(BaseModel):
    user_name: str
    email: EmailStr
    role_id: Optional[int] = None
    is_active: Optional[bool] = True   # default active
    created_by: Optional[int] = None


class UserResponse(BaseModel):
    user_id: int
    user_name: str
    email: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
    is_active: bool
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None