from typing import Optional
from pydantic import BaseModel
from enum import Enum


class LoginRequest(BaseModel):
    user_email: str
    user_password: str


class LoginResponse(BaseModel):
    status_code: int
    message: str
    user_id: Optional[int] = None
    email: Optional[str] = None
    name: Optional[str] = None
    access_token: Optional[str] = None
    temp_password: Optional[bool] = None
    password_expired: Optional[bool] = None
    remaining_attempts: Optional[int] = None
    token_type: Optional[str] = None
    user_role: Optional[str] = None


class AuditAction(str, Enum):
    login = "login"
    logout = "logout"


class AuditStatus(str, Enum):
    success = "success"
    failure = "failure"
