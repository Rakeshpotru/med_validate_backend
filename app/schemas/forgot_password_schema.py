from typing import Optional

from pydantic import BaseModel, EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str
    confirm_password: str

class SendResetResponse(BaseModel):
    status_code: int
    message: str
    user_id: Optional[int] = None

class VerifyOtpRequest(BaseModel):
    otp: str
    user_id: int