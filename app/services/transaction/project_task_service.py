import os
import logging
from sqlalchemy import select, insert, func,and_, update,join
from fastapi.responses import JSONResponse
from app.db.master import status
from app.db.transaction.project_task_users import project_task_users_table
from app.db.transaction.users import users as t_users_table
from app.db.transaction.project_tasks_list import project_tasks_list_table
from fastapi import status
from app.schemas.transaction.project_task_schema import UserResponseByTask
from app.schemas.transaction.task_schema import ProjectTaskTransferRequest

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



async def map_users_to_project_task_service(db, payload):
    try:
        logger.info("Start mapping users to project task.")

        # 1. Basic validation
        if not payload.project_task_id or not payload.user_ids:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "project_task_id and user_ids are required",
                    "data": [],
                },
            )

        project_task_id = payload.project_task_id
        selected_user_ids = set(payload.user_ids)

        # 2. Fetch current assignments
        query = select(
            project_task_users_table.c.project_task_user_map_id,
            project_task_users_table.c.user_id,
            project_task_users_table.c.user_is_active
        ).where(project_task_users_table.c.project_task_id == project_task_id)

        existing_rows = await db.fetch_all(query)
        existing_user_map = {row["user_id"]: row for row in existing_rows}

        # 3. Reactivate or insert selected users
        for user_id in selected_user_ids:
            if user_id in existing_user_map:
                if not existing_user_map[user_id]["user_is_active"]:
                    await db.execute(
                        update(project_task_users_table)
                        .where(
                            project_task_users_table.c.project_task_user_map_id
                            == existing_user_map[user_id]["project_task_user_map_id"]
                        )
                        .values(user_is_active=True)
                    )
            else:
                await db.execute(
                    insert(project_task_users_table).values(
                        project_task_id=project_task_id,
                        user_id=user_id,
                        user_is_active=True
                    )
                )

        # 4. Deactivate unselected users
        existing_user_ids = set(existing_user_map.keys())
        users_to_deactivate = existing_user_ids - selected_user_ids

        for user_id in users_to_deactivate:
            user_row = existing_user_map[user_id]
            # Deactivate user if they are currently active
            if user_row["user_is_active"]:
                await db.execute(
                    update(project_task_users_table)
                    .where(
                        and_(
                            project_task_users_table.c.project_task_id == project_task_id,
                            project_task_users_table.c.user_id == user_id,
                        )
                    )
                    .values(user_is_active=False)
                )
            else:
                logger.info(
                    f"User {user_id} is already inactive and not deactivated."
                )

        # 5. Update task_users_count based on active users
        query_active = select(project_task_users_table.c.user_id).where(
            and_(
                project_task_users_table.c.project_task_id == project_task_id,
                project_task_users_table.c.user_is_active == True
            )
        )
        active_rows = await db.fetch_all(query_active)
        active_count = len(active_rows)

        await db.execute(
            update(project_tasks_list_table)
            .where(project_tasks_list_table.c.project_task_id == project_task_id)
            .values(task_users_count=active_count)
        )

        logger.info(f"Users mapped to project task {project_task_id} successfully.")
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Users mapped to project task successfully",
                "data": {
                    "project_task_id": project_task_id,
                    "user_ids": list(selected_user_ids),
                    "active_users_count": active_count
                },
            },
        )

    except Exception as e:
        logger.error(f"Error mapping users to project task: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": [],
            },
        )


async def get_users_by_project_task_id(db, project_task_id: int):
    try:
        logger.info(f"Fetching users for project_task_id: {project_task_id}")

        # Join users with project_task_users
        j = join(
            t_users_table, project_task_users_table,
            t_users_table.c.user_id == project_task_users_table.c.user_id
        )

        query = select(t_users_table).select_from(j).where(
            and_(
                project_task_users_table.c.project_task_id == project_task_id,
                project_task_users_table.c.user_is_active == True
            )
        )

        results = await db.fetch_all(query)

        if not results:
            logger.warning(f"No users found for project_task_id {project_task_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No users found",
                    "data": []
                }
            )

        users = [UserResponseByTask(**row).dict() for row in results]

        logger.info(f"Users fetched successfully for project_task_id {project_task_id}.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Users fetched successfully",
                "data": users
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching users for project_task_id {project_task_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )


async def transfer_project_task_ownership_service(db, payload: ProjectTaskTransferRequest):
    try:
        logger.info(
            f"Transferring ownership of project_task_id {payload.project_task_id} "
            f"from user {payload.from_user_id} to user {payload.to_user_id}"
        )

        # Step 0: Validate input parameters
        if (
            not payload.project_task_id
            or not payload.from_user_id
            or not payload.to_user_id
            or not payload.task_transfer_reason
        ):
            logger.warning("Bad request: All parameters are required.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "All parameters are required: project_task_id, from_user_id, to_user_id, task_transfer_reason",
                    "data": []
                }
            )

        if payload.from_user_id == payload.to_user_id:
            logger.warning("Bad request: from_user_id and to_user_id cannot be the same.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "from_user_id and to_user_id cannot be the same",
                    "data": []
                }
            )

        # Step 1: Find the current active record
        query = select(project_task_users_table).where(
            and_(
                project_task_users_table.c.project_task_id == payload.project_task_id,
                project_task_users_table.c.user_id == payload.from_user_id,
                project_task_users_table.c.user_is_active == True
            )
        )
        record = await db.fetch_one(query)

        if not record:
            logger.warning(
                f"No active record found for project_task_id {payload.project_task_id} "
                f"and user_id {payload.from_user_id}"
            )
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No matching active record found for transfer",
                    "data": []
                }
            )

        # Step 2: Deactivate the previous record and store transfer info
        update_query = (
            project_task_users_table.update()
            .where(project_task_users_table.c.project_task_user_map_id == record.project_task_user_map_id)
            .values(
                user_is_active=False,
                to_user_id=payload.to_user_id,
                user_transfer_reason=payload.task_transfer_reason
            )
        )
        await db.execute(update_query)

        # Step 3: Insert a new record for the new owner
        insert_query = project_task_users_table.insert().values(
            project_task_id=payload.project_task_id,
            user_id=payload.to_user_id,
            user_is_active=True,
            submitted=False
        )
        await db.execute(insert_query)

        logger.info(f"Ownership transferred successfully for project_task_id {payload.project_task_id}.")

        # Step 4: Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Project task ownership transferred successfully",
                "data": {
                    "project_task_id": payload.project_task_id,
                    "from_user_id": payload.from_user_id,
                    "to_user_id": payload.to_user_id,
                    "task_transfer_reason": payload.task_transfer_reason
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while transferring project task ownership: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )
