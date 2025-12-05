import logging
from fastapi import APIRouter
from app.schemas.user_schema import LoginRequest, UserLoginResponse
from app.services.user_service import user_login_details

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login", response_model=UserLoginResponse)
async def login_user(login: LoginRequest):
    return await user_login_details(login)