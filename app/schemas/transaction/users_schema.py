from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Union


class UserBase(BaseModel):
    user_first_name: str
    user_middle_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: EmailStr
    user_phone: Optional[str] = None
    # user_password: Optional[str] = None
    role_id: int
    user_address: Optional[str] = None

class UserCreateRequest(BaseModel):
    users: Union[UserBase, List[UserBase]]
    created_by: int
    is_active: bool

class UserUpdateRequest(BaseModel):
    user_first_name: Optional[str] = Field(None, example="John")
    user_middle_name: Optional[str] = Field(None, example="M")
    user_last_name: Optional[str] = Field(None, example="Doe")
    user_phone: Optional[str] = Field(None, example="9876543210")
    user_address: Optional[str] = Field(None, example="123 Street Name")
    role_id: Optional[int] = Field(None, example=2)
    updated_by: int = Field(..., example=1)

class UserResponse(BaseModel):
    user_id: int
    user_first_name: str
    user_last_name: str
    user_email: EmailStr
    is_active: bool
# ================================



class UserDetailResponse(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    email: Optional[str] = None
    user_phone: Optional[str] = None
    user_address: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None


#=============
class UserImageData(BaseModel):
    user_id: int
    image_url: str

class UserImageResponse(BaseModel):
    status_code: int
    message: str
    data: UserImageData