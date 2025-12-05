# UserRoleMappingservice.py

import logging
from sqlalchemy import insert, select, update
from fastapi.responses import JSONResponse
from fastapi import status
from app.db.database import database
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.master.user_roles import user_roles_table
from app.schemas.transaction.user_role_mapping_schema import UserRoleMappingCreateRequest


logger = logging.getLogger(__name__)

async def create_user_role_mappings(data: UserRoleMappingCreateRequest):
    try:
        results = []
        message_list = []

        logger.info(f"Processing role mappings for user_id={data.user_id}, roles={data.role_ids}")

        for role_id in data.role_ids:
            logger.info(f"Checking role_id={role_id} for user_id={data.user_id}")

            # Check if role exists
            role_check_query = select(user_roles_table).where(user_roles_table.c.role_id == role_id)
            role_exists = await database.fetch_one(role_check_query)
            if not role_exists:
                logger.warning(f"Role {role_id} does not exist. Skipping.")
                message_list.append(f"Role {role_id} does not exist. Skipped.")
                continue

            # Check if mapping exists
            check_query = (
                select(user_role_mapping_table)
                .where(user_role_mapping_table.c.user_id == data.user_id)
                .where(user_role_mapping_table.c.role_id == role_id)
            )
            existing_record = await database.fetch_one(check_query)

            if existing_record:
                if not existing_record.is_active:
                    # Reactivate role
                    logger.info(f"Reactivating role_id={role_id} for user_id={data.user_id}")
                    update_query = (
                        update(user_role_mapping_table)
                        .where(user_role_mapping_table.c.user_role_map_id == existing_record.user_role_map_id)
                        .values(is_active=True)
                        .returning(
                            user_role_mapping_table.c.user_role_map_id,
                            user_role_mapping_table.c.user_id,
                            user_role_mapping_table.c.role_id,
                            user_role_mapping_table.c.is_active,
                        )
                    )
                    updated = await database.fetch_one(update_query)
                    results.append(dict(updated))
                    message_list.append(f"Role {role_id} reactivated for user {data.user_id}")
                else:
                    logger.info(f"Role {role_id} already active for user_id={data.user_id}")
                    message_list.append(f"Role {role_id} already assigned to user {data.user_id}")
            else:
                # Assign new role
                logger.info(f"Assigning new role_id={role_id} to user_id={data.user_id}")
                insert_query = (
                    insert(user_role_mapping_table)
                    .values(user_id=data.user_id, role_id=role_id, is_active=True)
                    .returning(
                        user_role_mapping_table.c.user_role_map_id,
                        user_role_mapping_table.c.user_id,
                        user_role_mapping_table.c.role_id,
                        user_role_mapping_table.c.is_active,
                    )
                )
                new_record = await database.fetch_one(insert_query)
                results.append(dict(new_record))
                message_list.append(f"Role {role_id} assigned to user {data.user_id}")

        combined_message = "\n".join(message_list) if message_list else "User role mappings processed successfully"
        logger.info(f"Role mapping processing completed for user_id={data.user_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": combined_message,
                "data": results
            }
        )

    except Exception as e:
        logger.error(f"Error processing user role mappings for user_id={data.user_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"An error occurred: {str(e)}",
                "data": None
            }
        )


async def get_roles_by_user_id(user_id: int):
    try:
        logger.info(f"Fetching roles for user_id={user_id}")

        # Query roles assigned to the user
        query = (
            select(
                user_role_mapping_table.c.role_id,
                user_roles_table.c.role_name,
                user_role_mapping_table.c.is_active
            )
            .join(user_roles_table, user_roles_table.c.role_id == user_role_mapping_table.c.role_id)
            .where(user_role_mapping_table.c.user_id == user_id)
        )

        rows = await database.fetch_all(query)
        data = [dict(row) for row in rows]

        if not data:
            logger.info(f"No roles found for user_id={user_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No roles found for user {user_id}",
                    "data": []
                }
            )

        logger.info(f"Roles fetched successfully for user_id={user_id}, count={len(data)}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Roles fetched successfully for user {user_id}",
                "data": data
            }
        )

    except Exception as e:
        logger.error(f"Error fetching roles for user_id={user_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"An error occurred: {str(e)}",
                "data": None
            }
        )


async def delete_user_role_mapping(user_id: int, role_id: int):
    try:
        logger.info(f"Attempting to delete user-role mapping: user_id={user_id}, role_id={role_id}")

        # Check if mapping exists
        query = (
            select(user_role_mapping_table)
            .where(user_role_mapping_table.c.user_id == user_id)
            .where(user_role_mapping_table.c.role_id == role_id)
        )
        record = await database.fetch_one(query)

        if not record:
            logger.warning(f"No mapping found for user_id={user_id} and role_id={role_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No mapping found for user {user_id} and role {role_id}",
                    "data": None
                }
            )

        if not record.is_active:
            logger.info(f"Mapping already inactive for user_id={user_id} and role_id={role_id}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": f"Mapping already inactive for user {user_id} and role {role_id}",
                    "data": None
                }
            )

        # Soft delete → set is_active = False
        update_query = (
            update(user_role_mapping_table)
            .where(user_role_mapping_table.c.user_role_map_id == record.user_role_map_id)
            .values(is_active=False)
            .returning(
                user_role_mapping_table.c.user_role_map_id,
                user_role_mapping_table.c.user_id,
                user_role_mapping_table.c.role_id,
                user_role_mapping_table.c.is_active
            )
        )
        updated_record = await database.fetch_one(update_query)

        logger.info(f"Mapping deactivated successfully: user_role_map_id={updated_record['user_role_map_id']}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": f"Mapping deactivated successfully for user {user_id} and role {role_id}",
                "data": dict(updated_record)
            }
        )

    except Exception as e:
        logger.error(f"Error deleting user-role mapping for user_id={user_id}, role_id={role_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"An error occurred: {str(e)}",
                "data": None
            }
        )
