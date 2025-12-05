from pydantic import BaseModel, EmailStr
from typing import Any, Optional, List, Union
from datetime import datetime

# Standard response schema
class APIResponse(BaseModel):
    status: str
    status_code: int
    message: str
    data: Optional[Any] = None


class UserData(BaseModel):
    user_first_name: str
    user_middle_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: EmailStr
    user_phone: Optional[str] = None
    # user_password: Optional[str] = None
    role_id: int
    user_address: Optional[str] = None

class UserRequest(BaseModel):
    users: Union[UserData, List[UserData]]
    created_by: int
    is_active: bool

class UserRoleMap(BaseModel):
    user_id: int
    role_id: int
    is_active: bool
    created_by: int
    

class UserResponse(BaseModel):
    user_id: int
    user_first_name: str
    user_middle_name: Optional[str] = None
    user_last_name: str
    user_email: EmailStr
    user_phone: Optional[str] = None
    role_id: Optional[int] = None
    is_active: bool
    user_address: Optional[str] = None
    created_by: Optional[int] = None
    created_date: Optional[datetime] = None

    class Config:
        orm_mode = True


class DeleteUserResponse(BaseModel):
    message: str


class UserUpdateRequest(BaseModel):
    user_first_name: Optional[str] = None
    user_middle_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_phone: Optional[str] = None
    user_address: Optional[str] = None
    role_id: Optional[int] = None
    updated_by: int  # Required for auditing
