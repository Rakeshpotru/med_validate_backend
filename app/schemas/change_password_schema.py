from pydantic import BaseModel, Field

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class ChangePasswordResponse(BaseModel):
    status_code: int
    detail: str
