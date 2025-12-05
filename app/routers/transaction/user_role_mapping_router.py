# UserRoleMappingrouter.py
from typing import List
from fastapi import APIRouter
from app.schemas.transaction.user_role_mapping_schema import UserRoleMappingResponse, UserRoleMappingCreateRequest
from app.services.transaction.user_role_mapping_service import create_user_role_mappings, get_roles_by_user_id, \
    delete_user_role_mapping

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])

@router.post("/CreateUserRoleMappings", response_model=List[UserRoleMappingResponse])
async def create_user_role_mappings_api(data: UserRoleMappingCreateRequest):
    return await create_user_role_mappings(data)


@router.get("/GetRolesByUserId/{user_id}")
async def get_roles_by_user_id_api(user_id: int):
    return await get_roles_by_user_id(user_id)


@router.delete("/DeleteUserRoleMapping/{user_id}/{role_id}")
async def delete_user_role_mapping_api(user_id: int, role_id: int):
    return await delete_user_role_mapping(user_id, role_id)