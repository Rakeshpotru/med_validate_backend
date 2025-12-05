import logging
import traceback

from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select,insert,update,delete,join
from datetime import datetime , timezone
from app.db import user_roles_table
from app.db.database import database
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.transaction.users import users
from app.schemas.transaction.t_users_schema import UserResponse, CreateUserRequest, UserUpdateRequest, UserDeleteRequest
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)

async def get_all_users():
    try:
        # LEFT OUTER JOIN: users -> user_role_mapping -> user_roles
        j = join(
            users,
            user_role_mapping_table,
            users.c.user_id == user_role_mapping_table.c.user_id,
            isouter=True,
        ).join(
            user_roles_table,
            user_role_mapping_table.c.role_id == user_roles_table.c.role_id,
            isouter=True,
        )

        # Build query
        query = (
            select(
                users.c.user_id,
                users.c.user_name,
                users.c.user_first_name,
                users.c.user_middle_name,
                users.c.user_last_name,
                users.c.email,
                users.c.user_phone,
                users.c.user_address,
                users.c.is_active,
                users.c.created_date,
                users.c.updated_date,
                user_role_mapping_table.c.role_id,
                user_roles_table.c.role_name,
                user_roles_table.c.is_active.label("role_is_active"),
                users.c.image_url
            )
            .select_from(j)
            .where(users.c.is_active == True)  # only active users
            .order_by(users.c.user_id.desc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=jsonable_encoder({
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No users found",
                    "data": [],
                }),
            )

        # Flatten role fields into top-level keys
        data = [
            {
                "user_id": r["user_id"],
                "user_name": r["user_name"],
                "user_first_name": r["user_first_name"],
                "user_middle_name": r["user_middle_name"],
                "user_last_name": r["user_last_name"],
                "email": r["email"],
                "user_phone": r["user_phone"],
                "user_address": r["user_address"],
                "is_active": r["is_active"],
                "created_date": r["created_date"],
                "updated_date": r["updated_date"],
                "role_id": r["role_id"],
                "role_name": r["role_name"],
                "image_url":r["image_url"]
            }
            for r in rows
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Users fetched successfully",
                "data": data,
            }),
        )

    except Exception as e:
        logger.error(f"Error fetching users: {e}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder({
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": [],
            }),
        )

async def create_user_with_role_service(user_data: CreateUserRequest):
    try:
        logger.info("Start creating a new user.")

        # Require role
        if not user_data.role_id and not getattr(user_data, "role_name", None):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Either role_id or role_name is required",
                    "data": [],
                },
            )

        default_password = "qwerty@123"

        # Check if email already exists
        query = select(users.c.user_id).where(users.c.email == user_data.email)
        existing_user_id = await database.fetch_val(query)

        if existing_user_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": f"Email '{user_data.email}' is already registered",
                    "data": [],
                },
            )

        # Resolve role_id (must be active)
        role_id = user_data.role_id
        if not role_id and getattr(user_data, "role_name", None):
            query = select(user_roles_table.c.role_id).where(
                user_roles_table.c.role_name.ilike(user_data.role_name),
                user_roles_table.c.is_active == True
            )
            role_id = await database.fetch_val(query)

        else:
            # Check directly if role_id is active
            query = select(user_roles_table.c.role_id).where(
                user_roles_table.c.role_id == role_id,
                user_roles_table.c.is_active == True
            )
            role_id = await database.fetch_val(query)

        if not role_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": f"Invalid or inactive role",
                    "data": [],
                },
            )

        now = datetime.now(timezone.utc)

        # Insert user
        insert_user_query = (
            insert(users)
            .values(
                user_name=user_data.user_name,
                email=user_data.email,
                password=default_password,
                is_active=user_data.is_active,
                created_by=user_data.created_by,
                created_date=now,
            )
            .returning(users.c.user_id)
        )
        new_user_id = await database.fetch_val(insert_user_query)

        # Insert mapping only if role is valid and active
        insert_mapping_query = (
            insert(user_role_mapping_table)
            .values(
                user_id=new_user_id,
                role_id=role_id,
                is_active=user_data.is_active,
            )
        )
        await database.execute(insert_mapping_query)

        logger.info("User created successfully with role mapping.")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "User created successfully",
                "data": {"user_id": new_user_id, "role_id": role_id},
            },
        )

    except Exception as e:
        logger.error(
            f"Internal server error while creating user: {str(e)}\n{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": [],
            },
        )


async def update_user_service(user_data: UserUpdateRequest):
    try:
        logger.info(f"Start updating user with id: {user_data.user_id}")

        # Check if user exists
        query = select(users).where(users.c.user_id == user_data.user_id)
        existing_user = await database.fetch_one(query)
        if not existing_user:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"User with id {user_data.user_id} not found",
                    "data": [],
                },
            )

        # Check if email is being updated to a new one and if it already exists
        if user_data.email != existing_user["email"]:
            query = select(users.c.user_id).where(users.c.email == user_data.email)
            email_exists = await database.fetch_val(query)
            if email_exists:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "status_code": status.HTTP_400_BAD_REQUEST,
                        "message": f"Email '{user_data.email}' is already registered",
                        "data": [],
                    },
                )

        now = datetime.now(timezone.utc)

        # Update user
        update_query = (
            update(users)
            .where(users.c.user_id == user_data.user_id)
            .values(
                user_name=user_data.user_name,
                email=user_data.email,
                updated_by=user_data.updated_by,
                updated_date=now,
            )
        )
        await database.execute(update_query)

        logger.info(f"User with id {user_data.user_id} updated successfully.")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "User updated successfully",
                "data": {"user_id": user_data.user_id},
            },
        )

    except Exception as e:
        logger.error(f"Internal server error while updating user: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": [],
            },
        )


async def delete_user_service(user_data: UserDeleteRequest):
    try:
        logger.info(f"Start soft deleting user with id: {user_data.user_id}")

        # Check if user exists
        query = select(users.c.user_id).where(users.c.user_id == user_data.user_id)
        existing_user_id = await database.fetch_val(query)

        if not existing_user_id:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"User with id {user_data.user_id} not found",
                    "data": [],
                },
            )

        # Soft delete by setting is_active = False
        delete_query = (
            update(users)
            .where(users.c.user_id == user_data.user_id)
            .values(is_active=False, updated_date=datetime.utcnow(),updated_by=user_data.updated_by)
        )
        await database.execute(delete_query)

        logger.info(f"User with id {user_data.user_id} soft deleted successfully")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "User deleted successfully",
                "data": {"user_id": user_data.user_id},
            },
        )

    except Exception as e:
        logger.error(f"Internal server error while deleting user: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": [],
            },
        )