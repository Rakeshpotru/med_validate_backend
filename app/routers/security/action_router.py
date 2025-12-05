from fastapi import APIRouter, Request
from app.schemas.security.actions_schema import (
    ActionCreate,
    ActionUpdate,
    ActionResponse,
    DeleteResponse,
    ResponseModel,
)
from app.services.security.actions_service import (
    get_all_actions_service,
    add_action_service,
    update_action_service,
    delete_action_service,
)

router = APIRouter(prefix="/screens", tags=["Screens APIs"])


# ✅ Get all actions
@router.get(
    "/getallactions",
    response_model=ResponseModel,
)
async def get_all_actions(request: Request):
    """
    API: Get all active actions
    """
    return await get_all_actions_service(request)


# ✅ Add action

@router.post("/add", response_model=ResponseModel)
async def add_action(request: Request, action: ActionCreate):
    # 👇 Get user_id from middleware
    user_id = request.state.user.get("user_id") if hasattr(request.state, "user") else None

    if not user_id:
        return {
            "status_code": 401,
            "message": "Unauthorized: User not found in request state",
            "data": None,
        }
    return await add_action_service(request, user_id)


# ✅ Update action

@router.put("/update/{action_id}")
async def update_action(request: Request, action_id: int):
    updated_by = request.state.user.get("user_id") if hasattr(request.state, "user") else None

    if not updated_by:
        return {
            "status_code": 401,
            "message": "Unauthorized: User not found in request state",
            "data": None,
        }
    return await update_action_service(request, action_id, updated_by)

# ✅ Delete action
@router.delete(
    "/delete/{action_id}",
    response_model=ResponseModel,
)
async def delete_action(request: Request, action_id: int):
    """
    API: Soft delete an action by ID (set is_active = false)
    """
    return await delete_action_service(request, action_id)
