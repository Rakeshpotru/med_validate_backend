from fastapi import APIRouter, Request
from app.schemas.security.roles_screen_schema import RoleIdRequest, RoleScreenActionsResponse, \
    ScreenActionMappingResponse, InsertRoleScreenActionsResponse, InsertRoleScreenActionsRequest, \
    InsertScreenActionMappingResponse, InsertScreenActionMappingRequest, RolePermissionResponse, RolePermissionRequest
from app.services.security.roles_screen_service import get_role_screen_actions_service, \
    get_screen_action_mapping_service, insert_role_screen_actions_service, \
    insert_screen_action_mapping_service, get_role_permissions_service

router = APIRouter(prefix="/screens", tags=["Screens APIs"])


# @router.get(
#     "/getallscreens",
#     response_model=ScreenListResponse
# )
# async def get_all_screens(request: Request):
#     """
#     API: Get all active screens
#     """
#     return await get_all_screens_service(request)


# @router.get(
#     "/getallactions",
#     response_model=ActionListResponse
# )
# async def get_all_actions(request: Request):
#     """
#     API: Get all active actions
#     """
#     return await get_all_actions_service(request)



@router.get(
    "/get-screen-action-mapping",
    response_model=ScreenActionMappingResponse
)
async def get_screen_action_mapping(request: Request):
    """
    API: Get all active screens with their mapped actions
    """
    return await get_screen_action_mapping_service(request)
@router.post(
    "/get-role-screen-actions-by-roleid",
    response_model=RoleScreenActionsResponse
)
async def get_role_screen_actions_by_roleid(
    request: Request,
    body: RoleIdRequest
):
    """
    API: Get all screen action mappings for a role
    """
    return await get_role_screen_actions_service(request, body.role_id)


@router.post(
    "/insert-role-screen-actions",
    response_model=InsertRoleScreenActionsResponse
)
async def insert_role_screen_actions(
    request: Request,
    body: InsertRoleScreenActionsRequest
):
    """
    API: Insert/Update role → screen → action mappings
    """
    return await insert_role_screen_actions_service(request, body)


@router.post(
    "/insert-screen-action-mapping",
    response_model=InsertScreenActionMappingResponse
)
async def insert_screen_action_mapping(
    request: Request,
    body: InsertScreenActionMappingRequest
):
    """
    API: Insert/Update screen → action mappings
    """
    return await insert_screen_action_mapping_service(request, body)


@router.post(
    "/get-role-permissions",
    response_model=RolePermissionResponse
)
async def get_role_permissions(request: Request, body: RolePermissionRequest):
    """
    API: Get role → screen → action permissions for a user
    """
    return await get_role_permissions_service(request, body.user_id)