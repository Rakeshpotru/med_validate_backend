from fastapi import APIRouter

from app.schemas.transaction.t_users_schema import CreateUserRequest, UserUpdateRequest, UserDeleteRequest
from app.services.transaction.t_users_service import get_all_users, create_user_with_role_service, update_user_service, \
    delete_user_service

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])

@router.get("/getallusers")
async def get_users():
    return await get_all_users()

@router.post("/CreateUser")
async def create_user(user_data: CreateUserRequest):
    """
    Create a new user with role.
    """
    return await create_user_with_role_service(user_data)


@router.put("/UpdateUser", response_model=dict)
async def update_user(user_data: UserUpdateRequest):
    """
    Update user details (name, email, is_active, updated_by)
    """
    return await update_user_service(user_data)


@router.delete("/DeleteUser")
async def delete_user(request: UserDeleteRequest):
    return await delete_user_service(request)