from fastapi import APIRouter, Request

from app.schemas.security.actions_schema import ResponseModel
from app.schemas.security.screens_schema import ScreenCreateRequest, ScreenResponse, ScreenUpdateRequest
from app.services.security.screens_service import (
    get_all_screens_service,
    add_screen_service,
    update_screen_service,
    delete_screen_service
)
from fastapi import Request

router = APIRouter(prefix="/screens", tags=["Screens APIs"])

@router.get("/getallscreens")
async def get_all_screens():
    return await get_all_screens_service()


# @router.post("/addscreen", response_model=ResponseModel)
# async def add_screen(screen: ScreenCreateRequest):
#     # Pass the fields directly to the service
#     return await add_screen_service(screen.ScreenName, screen.CreatedBy)

@router.post("/addscreen", response_model=ResponseModel)
async def add_screen(screen: ScreenCreateRequest, request: Request):
    user_id = request.state.user["user_id"]  # get from token
    return await add_screen_service(screen.ScreenName, user_id)


# ✅ Update action


@router.put("/updatescreen/{screen_id}", response_model=ScreenResponse)
async def update_screen(screen_id: int, screen: ScreenUpdateRequest, request: Request):
    user_id = request.state.user["user_id"]  # get from token
    return await update_screen_service(screen_id, screen.ScreenName, user_id)


# @router.put("/updatescreen/{screen_id}", response_model=ScreenResponse)
# async def update_screen(screen_id: int, screen: ScreenUpdateRequest):
#     # screen.ScreenName and screen.UpdatedBy come from Pydantic model
#     return await update_screen_service(screen_id, screen.ScreenName, screen.UpdatedBy)



# ✅ Delete action
# Router
@router.delete("/deletescreen/{screen_id}", response_model=ScreenResponse)
async def delete_screen(screen_id: int):
    """
    Soft delete a screen by ID (set is_active = FALSE)
    """
    return await delete_screen_service(screen_id)




