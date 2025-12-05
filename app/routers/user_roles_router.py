from fastapi import APIRouter

from app.schemas.user_roles_schema import UserRoleCreateRequest, UserRoleUpdateRequest, UserRoleDeleteRequest
from app.services.user_roles_service import get_all_user_roles, create_user_role, update_user_role, delete_user_role

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllUserRoles")
async def get_user_roles():
    return await get_all_user_roles()

@router.post("/createUserRole")
async def create_user_role_api(payload: UserRoleCreateRequest):
    return await create_user_role(payload)

@router.put("/updateUserRole")
async def update_user_role_api(payload: UserRoleUpdateRequest):
    return await update_user_role(payload)

@router.delete("/deleteUserRole")
async def delete_user_role_api(payload: UserRoleDeleteRequest):
    return await delete_user_role(payload)
