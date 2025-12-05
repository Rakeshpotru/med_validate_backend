

from fastapi import APIRouter
from app.schemas.forgot_password_schema import (
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
    SendResetResponse
)
from app.services.forgot_password_service import (
    process_forgot_password,
    process_verify_otp,
    process_reset_password
)

router = APIRouter()

@router.post("/forgot-password", response_model=SendResetResponse)
async def forgot_password(payload: ForgotPasswordRequest):
    return await process_forgot_password(payload)


@router.post("/verify-otp", response_model=SendResetResponse)
async def verify_otp(payload: VerifyOtpRequest):
    return await process_verify_otp(payload)


@router.post("/reset-password", response_model=SendResetResponse)
async def reset_password(payload: ResetPasswordRequest):
    return await process_reset_password(payload)
