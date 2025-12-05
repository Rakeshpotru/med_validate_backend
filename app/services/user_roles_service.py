import logging
from fastapi import status
from fastapi.responses import JSONResponse
from app.db.database import database
from app.db.master.user_roles import user_roles_table
from app.schemas.user_roles_schema import UserRoleResponse, UserRoleCreateRequest, UserRoleUpdateRequest, \
    UserRoleDeleteRequest
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)

async def get_all_user_roles():
    try:
        logger.info("Start to fetch all active user roles.")
        query = select(user_roles_table).where(user_roles_table.c.is_active == True).order_by(user_roles_table.c.role_id.desc())
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active user roles found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No user roles found",
                    "data": []
                }
            )

        result = [UserRoleResponse(**row) for row in rows]

        logger.info("User roles fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "User roles fetched successfully",
                "data": [r.dict() for r in result]
            }
        )
    except Exception as e:
        logger.error(f"Internal server error while fetching user roles: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def create_user_role(payload: UserRoleCreateRequest):
    try:
        logger.info("Start to create user role.")

        # 1. Validation: Role name required
        if not payload.role_name or payload.role_name.strip() == "":
            logger.warning("Role name is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role name is required",
                    "data": []
                }
            )

        # 2. Check if role exists (case-insensitive)
        query = select(user_roles_table).where(
            func.lower(user_roles_table.c.role_name) == payload.role_name.lower()
        )
        existing_role = await database.fetch_one(query)

        if existing_role:
            if existing_role.is_active:  # If already active
                logger.warning(f"Role '{payload.role_name}' already exists and is active.")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"Role '{payload.role_name}' already exists",
                        "data": []
                    }
                )
            else:
                # If inactive → Activate it
                update_query = (
                    user_roles_table.update()
                    .where(user_roles_table.c.role_id == existing_role.role_id)
                    .values(is_active=True)
                )
                await database.execute(update_query)

                logger.info(f"Inactive role '{payload.role_name}' activated with ID {existing_role.role_id}.")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": f"Role '{payload.role_name}' activated successfully",
                        "data": {
                            "role_id": existing_role.role_id,
                            "role_name": payload.role_name
                        }
                    }
                )

        # 3. Insert new role if not found
        insert_query = user_roles_table.insert().values(
            role_name=payload.role_name,
            is_active=payload.is_active
        )
        new_role_id = await database.execute(insert_query)

        logger.info(f"Role '{payload.role_name}' created successfully with ID {new_role_id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "User role created successfully",
                "data": {
                    "role_id": new_role_id,
                    "role_name": payload.role_name
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while creating user role: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def update_user_role(payload: UserRoleUpdateRequest):
    try:
        logger.info(f"Start to update role name for Role ID: {payload.role_id}")

        # 1. Validation
        if not payload.role_id:
            logger.warning("Role ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role ID is required",
                    "data": []
                }
            )

        if not payload.role_name or payload.role_name.strip() == "":
            logger.warning("Role name is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role name is required",
                    "data": []
                }
            )

        # 2. Check if role exists by ID
        query = select(user_roles_table).where(user_roles_table.c.role_id == payload.role_id)
        existing_role = await database.fetch_one(query)

        if not existing_role:
            logger.warning(f"Role ID {payload.role_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Role not found",
                    "data": []
                }
            )

        # 3. Check if new role name already exists for another role
        conflict_query = select(user_roles_table).where(
            and_(
                func.lower(user_roles_table.c.role_name) == payload.role_name.lower(),
                user_roles_table.c.role_id != payload.role_id,
                user_roles_table.c.is_active == True
            )
        )
        conflict_role = await database.fetch_one(conflict_query)

        if conflict_role:
            logger.warning(f"Role name '{payload.role_name}' already exists for another role.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"Role name '{payload.role_name}' already exists",
                    "data": []
                }
            )

        # 4. Update role name
        update_query = (
            user_roles_table.update()
            .where(user_roles_table.c.role_id == payload.role_id)
            .values(role_name=payload.role_name)
        )
        await database.execute(update_query)

        logger.info(f"Role ID {payload.role_id} updated successfully to '{payload.role_name}'.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Role updated successfully",
                "data": {
                    "role_id": payload.role_id,
                    "role_name": payload.role_name
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while updating user role: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def delete_user_role(payload: UserRoleDeleteRequest):
    try:
        logger.info(f"Start to delete (inactivate) user role. Role ID: {payload.role_id}")

        # 1. Validation
        if not payload.role_id:
            logger.warning("Role ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Role ID is required",
                    "data": []
                }
            )

        # 2. Check if role exists
        query = select(user_roles_table).where(user_roles_table.c.role_id == payload.role_id)
        existing_role = await database.fetch_one(query)

        if not existing_role:
            logger.warning(f"Role ID {payload.role_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Role not found",
                    "data": []
                }
            )

        # 3. Check if already inactive
        if not existing_role.is_active:
            logger.warning(f"Role ID {payload.role_id} is already inactive.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "Role is already inactive",
                    "data": []
                }
            )

        # 4. Update role to inactive
        update_query = (
            user_roles_table.update()
            .where(user_roles_table.c.role_id == payload.role_id)
            .values(is_active=False)
        )
        await database.execute(update_query)

        logger.info(f"Role ID {payload.role_id} marked as inactive successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Role inactivated successfully",
                "data": {
                    "role_id": payload.role_id,
                    "is_active": False
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while inactivating user role: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )
