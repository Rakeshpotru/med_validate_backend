# import logging
# from fastapi import APIRouter, Depends
# from app.schemas.change_password_schema import ChangePasswordRequest, ChangePasswordResponse
# from app.security import get_current_user
# from app.services.change_password_service import change_user_password

# logger = logging.getLogger(__name__)
# router = APIRouter()

# @router.post("/change-password", response_model=ChangePasswordResponse)
# async def change_password(
#     payload: ChangePasswordRequest,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#         Change user's password after validating current password,
#         enforcing complexity, and preventing password reuse.
#         """
#     return await change_user_password(payload, current_user)


import logging
from fastapi import APIRouter, Request
from app.schemas.change_password_schema import ChangePasswordRequest, ChangePasswordResponse
from app.services.change_password_service import change_user_password

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(payload: ChangePasswordRequest, request: Request):
    """
    Change user's password after validating current password,
    enforcing complexity, and preventing password reuse.
    """
    current_user = request.state.user  # ✅ Comes from auth_middleware
    return await change_user_password(payload, current_user)
