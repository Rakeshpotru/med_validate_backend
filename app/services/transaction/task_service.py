from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy import select,join,and_,func
from app.db.database import database
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.transaction.projects import projects
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.db.transaction.project_task_users import project_task_users_table
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.users import users as trans_user_table
from app.schemas.transaction.task_schema import UserTaskResponse, UserResponseByTask, AllTaskResponse
from app.db.transaction.projects_user_mapping import projects_user_mapping_table
from app.db.transaction.incident_reports import incident_report_table
from app.db.transaction.project_comments import project_comments_table
from app.db.docs.task_docs import task_docs_table
import logging
from fastapi.responses import JSONResponse
from fastapi import status, HTTPException
from app.db.transaction.users import users
import asyncio
from app.db.master.status import status_table
import json

logger = logging.getLogger(__name__)


# async def fetch_tasks_by_user_id(user_id: int) -> List[UserTaskResponse]:
#     query = (
#         select(
#             projects.c.project_id,
#             projects.c.project_name,
#             project_phases_list_table.c.phase_id,
#             sdlc_phases_table.c.phase_id,
#             sdlc_phases_table.c.phase_name,
#             project_tasks_list_table.c.project_task_id,
#             sdlc_tasks_table.c.task_name,
#             project_tasks_list_table.c.task_status_id,
#             projects.c.equipment_id,
#         )
#         .select_from(
#             project_task_users_table
#             .join(
#                 project_tasks_list_table,
#                 project_task_users_table.c.project_task_id == project_tasks_list_table.c.project_task_id
#             )
#             .join(
#                 project_phases_list_table,
#                 project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id
#             )
#             .join(
#                 projects,
#                 project_phases_list_table.c.project_id == projects.c.project_id
#             )
#             .join(
#                 sdlc_phases_table,
#                 project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id
#             )
#             .join(
#                 sdlc_tasks_table,
#                 project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id
#             )
#         )
#         .where(project_task_users_table.c.user_id == user_id)
#         .where(projects.c.is_active == True)
#         # Uncomment if your table actually has these columns:
#         # .where(project_tasks_list_table.c.is_active == True)
#         # .order_by(project_tasks_list_table.c.created_date.desc())
#     )
#
#     rows = await database.fetch_all(query)
#     return [UserTaskResponse(**dict(row)) for row in rows]



async def fetch_tasks_by_user_id(user_id: int):
    try:
        logger.info(f"Fetching tasks for user_id: {user_id}")

        query = (
            select(
                project_tasks_list_table.c.project_task_id.label("project_task_id"),
                projects.c.project_id,
                projects.c.project_name,
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                sdlc_tasks_table.c.task_name.label("task_name"),
                project_tasks_list_table.c.task_status_id.label("status_id"),
                func.bool_or(project_task_users_table.c.submitted).label("submitted"),  # aggregate boolean
                func.max(projects.c.created_date).label("created_date")
            )
            .select_from(
                project_task_users_table
                .join(
                    project_tasks_list_table,
                    project_task_users_table.c.project_task_id == project_tasks_list_table.c.project_task_id
                )
                .join(
                    project_phases_list_table,
                    project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id
                )
                .join(projects, project_phases_list_table.c.project_id == projects.c.project_id)
                .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
                .join(
                    sdlc_phase_tasks_mapping_table,
                    project_tasks_list_table.c.task_id == sdlc_phase_tasks_mapping_table.c.task_id
                )
                .join(
                    sdlc_tasks_table,
                    sdlc_phase_tasks_mapping_table.c.task_id == sdlc_tasks_table.c.task_id
                )
            )
            .where(project_task_users_table.c.user_id == user_id)
            .group_by(
                project_tasks_list_table.c.project_task_id,
                projects.c.project_id,
                projects.c.project_name,
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                sdlc_tasks_table.c.task_name,
                project_tasks_list_table.c.task_status_id
            )
            .order_by(project_tasks_list_table.c.project_task_id.desc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            logger.warning(f"No tasks found for user_id {user_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No tasks assigned to this user",
                    "data": []
                }
            )

        tasks = [UserTaskResponse(**dict(row)) for row in rows]

        logger.info(f"Tasks fetched successfully for user_id {user_id}.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Tasks assigned to user retrieved successfully",
                "data": [task.dict() for task in tasks]
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching tasks for user_id {user_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )



async def get_all_tasks():
    try:
        logger.info("Start fetching all tasks.")

        # Build query (same as your version)
        query = (
            select(
                projects.c.project_id,
                projects.c.project_name,
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                project_tasks_list_table.c.project_task_id,
                sdlc_tasks_table.c.task_name,
                project_tasks_list_table.c.task_status_id.label("status_id"),
                func.string_agg(func.distinct(users.c.user_name), ", ").label("users"),
                project_tasks_list_table.c.created_date,
            )
            .select_from(
                project_tasks_list_table
                .join(project_phases_list_table, project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id)
                .join(projects, project_phases_list_table.c.project_id == projects.c.project_id)
                .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
                .join(sdlc_phase_tasks_mapping_table, (project_tasks_list_table.c.task_id == sdlc_phase_tasks_mapping_table.c.task_id) & (sdlc_phase_tasks_mapping_table.c.is_active == True))
                .join(sdlc_tasks_table, sdlc_phase_tasks_mapping_table.c.task_id == sdlc_tasks_table.c.task_id)
                .join(project_task_users_table,project_task_users_table.c.project_task_id == project_tasks_list_table.c.project_task_id)  # 👈 mapping
                .join(users, project_task_users_table.c.user_id == users.c.user_id)
            )
            .group_by(
                projects.c.project_id,
                projects.c.project_name,
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                project_tasks_list_table.c.project_task_id,
                sdlc_tasks_table.c.task_name,
                project_tasks_list_table.c.task_status_id,
                project_tasks_list_table.c.created_date,
            )
            .order_by(project_tasks_list_table.c.created_date.desc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No tasks found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No tasks found",
                    "data": []
                }
            )

        # ------------------------
        # Group into nested format
        # ------------------------
        projects_dict = {}

        for row in rows:
            row_dict = dict(row)
            created_date = row_dict["created_date"].isoformat() if isinstance(row_dict["created_date"], datetime) else row_dict["created_date"]

            proj_id = row_dict["project_id"]
            phase_id = row_dict["phase_id"]

            # Initialize project if not exists
            if proj_id not in projects_dict:
                projects_dict[proj_id] = {
                    "project_id": proj_id,
                    "project_name": row_dict["project_name"],
                    "phases": {}
                }

            # Initialize phase if not exists
            if phase_id not in projects_dict[proj_id]["phases"]:
                projects_dict[proj_id]["phases"][phase_id] = {
                    "phase_id": phase_id,
                    "phase_name": row_dict["phase_name"],
                    "tasks": []
                }

            # Add task
            projects_dict[proj_id]["phases"][phase_id]["tasks"].append({
                "project_task_id": row_dict["project_task_id"],
                "task_name": row_dict["task_name"],
                "status_id": row_dict["status_id"],
                "created_date": created_date,
                "users": row_dict["users"],
            })

        # Convert dicts to list
        final_data = []
        for proj in projects_dict.values():
            proj["phases"] = list(proj["phases"].values())
            final_data.append(proj)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Tasks fetched successfully",
                "data": final_data
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching tasks: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

# ----------new----------
# async def get_user_tasks_service(db, user_id: int, project_id: int):
#     try:
#         logger.info(f"Fetching tasks for user_id={user_id}, project_id={project_id}")
#
#         # Validate user_id
#         if not user_id or user_id <= 0:
#             logger.warning(f"Bad Request: Invalid user_id={user_id}")
#             return {
#                 "status_code": status.HTTP_400_BAD_REQUEST,
#                 "message": "Invalid user_id provided",
#                 "data": [],
#             }
#
#         # Step 1: Get all active projects mapped to the given user
#         projects_query = (
#             select(
#                 projects.c.project_id,
#                 projects.c.project_name
#             )
#             .select_from(
#                 projects.join(
#                     projects_user_mapping_table,
#                     projects.c.project_id == projects_user_mapping_table.c.project_id,
#                 )
#             )
#             .where(
#                 projects_user_mapping_table.c.user_id == user_id,
#                 projects_user_mapping_table.c.is_active == True,
#                 projects.c.is_active == True,
#             )
#         )
#
#         if project_id and project_id != 0:
#             projects_query = projects_query.where(projects.c.project_id == project_id)
#
#         project_rows = await db.fetch_all(projects_query)
#         project_map = {row.project_id: row.project_name for row in project_rows}
#         project_ids = list(project_map.keys())
#
#         if not project_ids:
#             logger.info(f"No matching projects found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No matching projects found",
#                 "data": [],
#             }
#
#         # Step 2: Get all phases for these projects
#         phases_query = (
#             select(
#                 project_phases_list_table.c.project_phase_id,
#                 project_phases_list_table.c.phase_id,
#                 project_phases_list_table.c.project_id,
#                 sdlc_phases_table.c.phase_name,
#             )
#             .select_from(
#                 project_phases_list_table.join(
#                     sdlc_phases_table,
#                     project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id,
#                 )
#             )
#             .where(project_phases_list_table.c.project_id.in_(project_ids))
#             .order_by(project_phases_list_table.c.phase_order_id)
#         )
#
#         phase_rows = await db.fetch_all(phases_query)
#
#         if not phase_rows:
#             logger.info(f"No phases found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No phases found for the selected project(s)",
#                 "data": [],
#             }
#
#         # Group phases by phase_id to avoid duplicates
#         phase_map = {}
#         for phase in phase_rows:
#             if phase.phase_id not in phase_map:
#                 phase_map[phase.phase_id] = {
#                     "phase_id": phase.phase_id,
#                     "phase_name": phase.phase_name,
#                     "tasks": []
#                 }
#
#         # Step 3: Fetch tasks for each unique phase
#         for phase_id, phase_data in phase_map.items():
#             project_phase_ids = [
#                 p.project_phase_id for p in phase_rows if p.phase_id == phase_id
#             ]
#
#             tasks_query = (
#                 select(
#                     project_tasks_list_table.c.project_task_id,
#                     project_tasks_list_table.c.task_id,
#                     project_tasks_list_table.c.project_phase_id,
#                     sdlc_tasks_table.c.task_name,
#                     sdlc_tasks_table.c.task_description,
#                     project_phases_list_table.c.project_id,
#                     project_tasks_list_table.c.task_start_date,
#                     project_tasks_list_table.c.task_end_date
#                 )
#                 .select_from(
#                     project_tasks_list_table
#                     .join(
#                         project_task_users_table,
#                         project_tasks_list_table.c.project_task_id == project_task_users_table.c.project_task_id,
#                     )
#                     .join(
#                         sdlc_tasks_table,
#                         project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id,
#                     )
#                     .join(
#                         project_phases_list_table,
#                         project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id,
#                     )
#                 )
#                 .where(
#                     project_tasks_list_table.c.project_phase_id.in_(project_phase_ids),
#                     project_task_users_table.c.user_id == user_id,
#                     project_task_users_table.c.user_is_active == True
#                 )
#                 .order_by(project_tasks_list_table.c.task_order_id)
#             )
#
#             task_rows = await db.fetch_all(tasks_query)
#
#             for task in task_rows:
#                 # Step 4: Fetch all users mapped to this task
#                 task_users_query = (
#                     select(
#                         users.c.user_id,
#                         users.c.user_name
#                         users.c.image_url
#                     )
#                     .select_from(
#                         users.join(
#                             project_task_users_table,
#                             users.c.user_id == project_task_users_table.c.user_id
#                         )
#                     )
#                     .where(
#                         project_task_users_table.c.project_task_id == task.project_task_id,
#                         project_task_users_table.c.user_is_active == True
#                     )
#                 )
#                 task_user_rows = await db.fetch_all(task_users_query)
#
#                 # Step 5: Count incident reports for this task
#                 incident_count_query = (
#                     select(func.count(incident_report_table.c.incident_report_id))
#                     .where(incident_report_table.c.task_id == task.project_task_id)
#                 )
#                 incident_count = await db.fetch_val(incident_count_query)
#
#                 # Step 6: Count project comments for this task
#                 comment_count_query = (
#                     select(func.count(project_comments_table.c.comment_id))
#                     .where(project_comments_table.c.project_task_id == task.project_task_id)
#                 )
#                 comment_count = await db.fetch_val(comment_count_query)
#
#                 # Step 7: Count task documents for this task
#                 docs_count_query = (
#                     select(func.count(task_docs_table.c.task_doc_id))
#                     .where(task_docs_table.c.project_task_id == task.project_task_id)
#                 )
#                 docs_count = await db.fetch_val(docs_count_query)
#
#                 # Calculate left days (if task_end_date exists)
#                 left_days = None
#                 if task.task_end_date:
#                     current_date = datetime.now(timezone.utc)
#                     left_days = (task.task_end_date - current_date).days
#                     if left_days < 0:  # if past due date
#                         left_days = 0
#
#                 phase_data["tasks"].append({
#                     "task_id": task.task_id,
#                     "project_task_id": task.project_task_id,
#                     "task_name": task.task_name,
#                     "task_description": task.task_description,
#                     "project_id": task.project_id,
#                     "project_name": project_map.get(task.project_id, " "),
#                     "task_start_date": task.task_start_date.isoformat() if task.task_start_date else None,
#                     "task_end_date": task.task_end_date.isoformat() if task.task_end_date else None,
#                     "left_days": left_days,
#                     "incident_reports_count": incident_count or 0,
#                     "task_comments_count": comment_count or 0,
#                     "task_docs_count": docs_count or 0,
#                     "users": [ {"user_id": u.user_id,"user_name": u.user_name,"user_image": u.image_url} for u in task_user_rows ],
#                 })
#
#         # Step 8: Only include phases with tasks
#         response_data = [phase for phase in phase_map.values() if phase["tasks"]]
#
#         if not response_data:
#             logger.info(f"No tasks found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No tasks found for the selected project(s) and user",
#                 "data": [],
#             }
#
#         logger.info(f"Tasks fetched successfully for user_id={user_id}, project_id={project_id}")
#         return {
#             "status_code": status.HTTP_200_OK,
#             "message": "Tasks fetched successfully",
#             "data": response_data,
#         }
#
#     except Exception as e:
#         logger.error(f"Error fetching tasks for user_id={user_id}, project_id={project_id}: {str(e)}")
#         return {
#             "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#             "message": f"Internal server error: {str(e)}",
#             "data": [],
#         }




# async def get_user_tasks_service(db, user_id: int, project_id: int):
#     try:
#         logger.info(f"Fetching tasks for user_id={user_id}, project_id={project_id}")
#
#         # Validate user_id
#         if not user_id or user_id <= 0:
#             logger.warning(f"Bad Request: Invalid user_id={user_id}")
#             return {
#                 "status_code": status.HTTP_400_BAD_REQUEST,
#                 "message": "Invalid user_id provided",
#                 "data": [],
#             }
#
#         # Step 1: Get all active projects mapped to the given user
#         projects_query = (
#             select(
#                 projects.c.project_id,
#                 projects.c.project_name
#             )
#             .select_from(
#                 projects.join(
#                     projects_user_mapping_table,
#                     projects.c.project_id == projects_user_mapping_table.c.project_id,
#                 )
#             )
#             .where(
#                 projects_user_mapping_table.c.user_id == user_id,
#                 projects_user_mapping_table.c.is_active == True,
#                 projects.c.is_active == True,
#             )
#         )
#
#         if project_id and project_id != 0:
#             projects_query = projects_query.where(projects.c.project_id == project_id)
#
#         project_rows = await db.fetch_all(projects_query)
#         project_map = {row.project_id: row.project_name for row in project_rows}
#         project_ids = list(project_map.keys())
#
#         if not project_ids:
#             logger.info(f"No matching projects found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No matching projects found",
#                 "data": [],
#             }
#
#         # Step 2: Get all phases for these projects
#         phases_query = (
#             select(
#                 project_phases_list_table.c.project_phase_id,
#                 project_phases_list_table.c.phase_id,
#                 project_phases_list_table.c.project_id,
#                 sdlc_phases_table.c.phase_name,
#             )
#             .select_from(
#                 project_phases_list_table.join(
#                     sdlc_phases_table,
#                     project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id,
#                 )
#             )
#             .where(project_phases_list_table.c.project_id.in_(project_ids))
#             .order_by(project_phases_list_table.c.phase_order_id)
#         )
#
#         phase_rows = await db.fetch_all(phases_query)
#
#         if not phase_rows:
#             logger.info(f"No phases found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No phases found for the selected project(s)",
#                 "data": [],
#             }
#
#         # Group phases by phase_id to avoid duplicates
#         phase_map = {}
#         for phase in phase_rows:
#             if phase.phase_id not in phase_map:
#                 phase_map[phase.phase_id] = {
#                     "phase_id": phase.phase_id,
#                     "phase_name": phase.phase_name,
#                     "tasks": []
#                 }
#
#         # Step 3: Fetch tasks for each unique phase in parallel
#         async def fetch_task_details(phase_id, phase_data):
#             project_phase_ids = [
#                 p.project_phase_id for p in phase_rows if p.phase_id == phase_id
#             ]
#
#             tasks_query = (
#                 select(
#                     project_tasks_list_table.c.project_task_id,
#                     project_tasks_list_table.c.task_id,
#                     project_tasks_list_table.c.project_phase_id,
#                     sdlc_tasks_table.c.task_name,
#                     sdlc_tasks_table.c.task_description,
#                     project_phases_list_table.c.project_id,
#                     project_tasks_list_table.c.task_start_date,
#                     project_tasks_list_table.c.task_end_date,
#                     project_tasks_list_table.c.task_status_id,
#                     status_table.c.status_name.label("task_status_name"),
#                 )
#                 .select_from(
#                     project_tasks_list_table
#                     .join(
#                         project_task_users_table,
#                         project_tasks_list_table.c.project_task_id == project_task_users_table.c.project_task_id,
#                     )
#                     .join(
#                         sdlc_tasks_table,
#                         project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id,
#                     )
#                     .join(
#                         project_phases_list_table,
#                         project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id,
#                     )
#                     .outerjoin(
#                         status_table,
#                         project_tasks_list_table.c.task_status_id == status_table.c.status_id,
#                     )
#                 )
#                 .where(
#                     project_tasks_list_table.c.project_phase_id.in_(project_phase_ids),
#                     project_task_users_table.c.user_id == user_id,
#                     project_task_users_table.c.user_is_active == True
#                 )
#                 .order_by(project_tasks_list_table.c.task_order_id)
#             )
#
#             task_rows = await db.fetch_all(tasks_query)
#
#             for task in task_rows:
#                 # Step 4: Fetch all users mapped to this task
#                 task_users_query = (
#                     select(
#                         users.c.user_id,
#                         users.c.user_name,
#                         users.c.image_url
#                     )
#                     .select_from(
#                         users.join(
#                             project_task_users_table,
#                             users.c.user_id == project_task_users_table.c.user_id
#                         )
#                     )
#                     .where(
#                         project_task_users_table.c.project_task_id == task.project_task_id,
#                         project_task_users_table.c.user_is_active == True
#                     )
#                 )
#                 task_user_rows = await db.fetch_all(task_users_query)
#
#                 # Step 5: Count incident reports, comments, docs concurrently
#                 async def fetch_task_counts(task_id):
#                     incident_count_query = (
#                         select(func.count(incident_report_table.c.incident_report_id))
#                         .where(incident_report_table.c.task_id == task_id)
#                     )
#                     comment_count_query = (
#                         select(func.count(project_comments_table.c.comment_id))
#                         .where(project_comments_table.c.project_task_id == task_id)
#                     )
#                     docs_count_query = (
#                         select(func.count(task_docs_table.c.task_doc_id))
#                         .where(task_docs_table.c.project_task_id == task_id)
#                     )
#
#                     # Run all three counts concurrently
#                     incident_count, comment_count, docs_count = await asyncio.gather(
#                         db.fetch_val(incident_count_query),
#                         db.fetch_val(comment_count_query),
#                         db.fetch_val(docs_count_query),
#                     )
#
#                     return incident_count or 0, comment_count or 0, docs_count or 0
#
#                 # Fetch task counts concurrently
#                 incident_count, comment_count, docs_count = await fetch_task_counts(task.project_task_id)
#
#                 # Calculate left days (if task_end_date exists)
#                 left_days = None
#                 if task.task_end_date:
#                     current_date = datetime.now(timezone.utc)
#                     left_days = (task.task_end_date - current_date).days
#                     if left_days < 0:
#                         left_days = 0
#
#                 phase_data["tasks"].append({
#                     "task_id": task.task_id,
#                     "project_task_id": task.project_task_id,
#                     "task_name": task.task_name,
#                     "task_description": task.task_description,
#                     "project_id": task.project_id,
#                     "project_name": project_map.get(task.project_id, " "),
#                     "task_start_date": task.task_start_date.isoformat() if task.task_start_date else None,
#                     "task_end_date": task.task_end_date.isoformat() if task.task_end_date else None,
#                     "left_days": left_days,
#                     "task_status_id": task.task_status_id,
#                     "task_status_name": task.task_status_name,
#                     "incident_reports_count": incident_count,
#                     "task_comments_count": comment_count,
#                     "task_docs_count": docs_count,
#                     "users": [{"user_id": u.user_id, "user_name": u.user_name, "user_image":u.image_url} for u in task_user_rows],
#                 })
#
#         # Run fetch_task_details for each phase in parallel
#         await asyncio.gather(
#             *(fetch_task_details(phase_id, phase_data) for phase_id, phase_data in phase_map.items())
#         )
#
#         # Step 8: Only include phases with tasks
#         response_data = [phase for phase in phase_map.values() if phase["tasks"]]
#
#         if not response_data:
#             logger.info(f"No tasks found for user_id={user_id}, project_id={project_id}")
#             return {
#                 "status_code": status.HTTP_404_NOT_FOUND,
#                 "message": "No tasks found for the selected project(s) and user",
#                 "data": [],
#             }
#
#         logger.info(f"Tasks fetched successfully for user_id={user_id}, project_id={project_id}")
#         return {
#             "status_code": status.HTTP_200_OK,
#             "message": "Tasks fetched successfully",
#             "data": response_data,
#         }
#
#     except Exception as e:
#         logger.error(f"Error fetching tasks for user_id={user_id}, project_id={project_id}: {str(e)}")
#         return {
#             "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#             "message": f"Internal server error: {str(e)}",
#             "data": [],
#         }

