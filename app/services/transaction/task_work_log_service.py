import logging
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from app.db.database import database
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.project_task_users import project_task_users_table
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.transaction.projects import projects
from app.db.transaction.task_work_log import task_work_log_table
from app.db.transaction.users import users
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.db.master.status import status_table
from app.db.master.sdlc_phases import sdlc_phases_table
from datetime import datetime, timezone
from app.schemas.transaction.task_work_log_schema import TaskWorkLogCreateRequest
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

# async def get_task_work_log_details_by_project_task_id(project_task_id: int):
#     try:
#         logger.info(f"Fetching task work log details for project_task_id: {project_task_id}")
#
#         # 1️⃣ Validate if project_task_id exists
#         project_task_query = select(project_tasks_list_table).where(
#             project_tasks_list_table.c.project_task_id == project_task_id
#         )
#         project_task = await database.fetch_one(project_task_query)
#
#         if not project_task:
#             logger.warning(f"Project task ID {project_task_id} not found.")
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": "Project task not found",
#                     "data": []
#                 }
#             )
#
#         # 2️⃣ Task info
#         task_query = select(
#             sdlc_tasks_table.c.task_name
#         ).where(sdlc_tasks_table.c.task_id == project_task.task_id)
#         task = await database.fetch_one(task_query)
#
#         # 3️⃣ Status info
#         status_query = select(
#             status_table.c.status_name
#         ).where(status_table.c.status_id == project_task.task_status_id)
#         status_data = await database.fetch_one(status_query)
#
#         # 4️⃣ Phase and project info
#         phase_query = select(project_phases_list_table).where(
#             project_phases_list_table.c.project_phase_id == project_task.project_phase_id
#         )
#         phase_data = await database.fetch_one(phase_query)
#
#         project_name = None
#         phase_name = None
#         if phase_data:
#             # project name
#             project_query = select(projects.c.project_name).where(
#                 projects.c.project_id == phase_data.project_id
#             )
#             project_row = await database.fetch_one(project_query)
#             project_name = project_row.project_name if project_row else None
#
#             # phase name
#             phase_name_query = select(sdlc_phases_table.c.phase_name).where(
#                 sdlc_phases_table.c.phase_id == phase_data.phase_id
#             )
#             phase_row = await database.fetch_one(phase_name_query)
#             phase_name = phase_row.phase_name if phase_row else None
#
#         # 5️⃣ Users mapped to this task
#         user_map_query = (
#             select(
#                 project_task_users_table.c.user_id,
#                 users.c.user_name,
#                 users.c.image_url
#             )
#             .join(users, users.c.user_id == project_task_users_table.c.user_id)
#             .where(project_task_users_table.c.project_task_id == project_task_id)
#         )
#         user_rows = await database.fetch_all(user_map_query)
#         users_data = [{"user_id": u.user_id, "user_name": u.user_name, "image_url":u.image_url} for u in user_rows]
#
#         # 6️⃣ Task work logs
#         work_log_query = (
#             select(
#                 task_work_log_table.c.task_work_log_id,
#                 task_work_log_table.c.user_id,
#                 users.c.user_name,
#                 users.c.image_url,
#                 task_work_log_table.c.remarks,
#                 task_work_log_table.c.created_date
#             )
#             .join(users, users.c.user_id == task_work_log_table.c.user_id)
#             .where(task_work_log_table.c.project_task_id == project_task_id)
#             .order_by(task_work_log_table.c.task_work_log_id.asc())
#         )
#         work_logs = await database.fetch_all(work_log_query)
#         work_logs_data = [
#             {
#                 "task_work_log_id": w.task_work_log_id,
#                 "user_id": w.user_id,
#                 "user_name": w.user_name,
#                 "image_url": w.image_url,
#                 "remarks": w.remarks,
#                 "created_date": str(w.created_date)
#             } for w in work_logs
#         ]
#
#         # 7️⃣ Combine all data
#         response_data = {
#             "project_task_id": project_task.project_task_id,
#             "task_id": project_task.task_id,
#             "task_name": task.task_name if task else None,
#             "task_status_id": project_task.task_status_id,
#             "status_name": status_data.status_name if status_data else None,
#             "project_phase_id": project_task.project_phase_id,
#             "project_id": phase_data.project_id if phase_data else None,
#             "phase_id": phase_data.phase_id if phase_data else None,
#             "project_name": project_name,
#             "phase_name": phase_name,
#             "users": users_data,
#             "work_logs": work_logs_data
#         }
#
#         logger.info("Task work log details fetched successfully.")
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Task work log details fetched successfully",
#                 "data": response_data
#             }
#         )
#
#     except Exception as e:
#         logger.error(f"Error while fetching task work log details: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": "Internal server error",
#                 "data": []
#             }
#         )

async def get_task_work_log_details_by_project_task_id(project_task_id: int):
    try:
        logger.info(f"Calling DB function for project_task_id: {project_task_id}")

        query = text(
            "SELECT ai_verify_transaction.get_task_work_log_details_by_project_task_id(:project_task_id)"
        ).bindparams(project_task_id=project_task_id)

        result = await database.fetch_one(query)

        if result and result[0] is not None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=json.loads(result[0])
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status_code": 500,
                    "message": "Unexpected error or null response from DB function",
                    "data": []
                }
            )

    except Exception as e:
        logger.error(f"Error in service: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": 500,
                "message": "Internal server error",
                "data": []
            }
        )


async def create_task_work_log(payload: TaskWorkLogCreateRequest):
    try:
        logger.info("Start to create task work log entry.")

        # 1️⃣ Validate project_task_id
        project_task_query = select(project_tasks_list_table.c.project_task_id).where(
            project_tasks_list_table.c.project_task_id == payload.project_task_id
        )
        project_task = await database.fetch_one(project_task_query)

        if not project_task:
            logger.warning(f"Project Task ID {payload.project_task_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Invalid project_task_id — not found in project_tasks_list_table",
                    "data": []
                }
            )

        # 2️⃣ Validate user_id
        user_query = select(users.c.user_id).where(users.c.user_id == payload.user_id)
        user = await database.fetch_one(user_query)

        if not user:
            logger.warning(f"User ID {payload.user_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Invalid user_id — not found in users table",
                    "data": []
                }
            )

        # 3️⃣ Insert record
        # current_time = datetime.now(timezone.utc)
        insert_query = task_work_log_table.insert().values(
            project_task_id=payload.project_task_id,
            user_id=payload.user_id,
            remarks=payload.remarks,
            # created_date=current_time
        )
        new_log_id = await database.execute(insert_query)

        logger.info(f"Task work log created successfully with ID {new_log_id}.")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Task work log created successfully",
                "data": {
                    "task_work_log_id": new_log_id
                }
            }
        )

    except Exception as e:
        logger.error(f"Error while creating task work log: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def update_project_task_status(project_task_id: int, task_status_id: int):
    try:
        logger.info(f"Updating task_status_id for project_task_id: {project_task_id}")
        # Validate required fields
        if not project_task_id or not task_status_id:
            logger.warning("Missing required fields: project_task_id or task_status_id")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "fields are required",
                    "data": []
                }
            )
        # Check if project_task_id exists
        query_check = project_tasks_list_table.select().where(
            project_tasks_list_table.c.project_task_id == project_task_id
        )
        existing_task = await database.fetch_one(query_check)

        if not existing_task:
            logger.warning(f"Project task ID {project_task_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project task not found",
                    "data": []
                }
            )

        # Update task_status_id
        update_query = (
            project_tasks_list_table.update()
            .where(project_tasks_list_table.c.project_task_id == project_task_id)
            .values(task_status_id=task_status_id)
        )
        await database.execute(update_query)

        logger.info(f"Task status updated successfully for project_task_id: {project_task_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Task status updated successfully",
                "data": {
                    "project_task_id": project_task_id,
                    "task_status_id": task_status_id
                }
            }
        )

    except Exception as e:
        logger.error(f"Error while updating task status: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )