
from fastapi import APIRouter, BackgroundTasks, Request, status,UploadFile,File

from fastapi.responses import JSONResponse
from app.schemas.transaction.users_schema import UserCreateRequest, UserUpdateRequest, UserImageResponse, \
    UserDetailResponse
from app.services.transaction.users_service import (
    create_user_service,
    update_user_service,
    upload_user_profile_image_service, get_user_by_id_service, delete_user_profile_image_service,
)

router = APIRouter(prefix="/users", tags=["Users"])



@router.post("/NewCreateUser", status_code=status.HTTP_201_CREATED)
async def register_user(req: UserCreateRequest, background_tasks: BackgroundTasks, request: Request):
    return await create_user_service(req, background_tasks)



@router.put(
    "/NewUpdateUser/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Update user fields",
    description="Update selected fields for an existing user by user_id"
)
async def update_user(user_id: int, user_data: UserUpdateRequest):
    print("🟢 Received user_id:", user_id)

    """
    Endpoint: Update selected user fields if they are provided in the request.
    """
    return await update_user_service(user_id, user_data)


@router.get(
    "/getUserById/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Fetch a single user's details by ID"
)
async def get_user_by_id(user_id: int):
    """
    Get detailed info about a user, including role name and profile image.
    """
    return await get_user_by_id_service(user_id)



@router.post("/{user_id}/upload-image", response_model=UserImageResponse)
async def upload_user_profile_image(user_id: int, file: UploadFile = File(...)):
    result = await upload_user_profile_image_service(user_id, file)
    return result

@router.delete("/{user_id}/delete-image", status_code=status.HTTP_200_OK)
async def delete_user_profile_image(user_id: int):
    """
    Deletes user's profile image (file + DB reference).
    """
    result = await delete_user_profile_image_service(user_id)
    return result