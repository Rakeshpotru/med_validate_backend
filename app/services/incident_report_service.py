from datetime import datetime
from http.client import HTTPException
from operator import or_
from typing import Optional
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import and_, case, desc, func, insert, update, select

from app.db.database import database
# from app.db import incident_report, project_tasks, project_phases, projects  # adjust imports
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.db.transaction.json_template_transactions import json_template_transactions
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.transaction.projects import projects
from app.db.transaction.incident_reports import incident_report_table,incident_reports_table,incident_report_transactions
from app.db.docs.task_docs import task_docs_table
from app.db.transaction.users import users
from app.schemas.transaction.incident_reports_schema import IncidentCreateRequest, RaiseIncidentOut  # pydantic model
from app.db import user_role_mapping_table, user_roles_table

import logging

logger = logging.getLogger(__name__)


async def create_incident_report(db, incident: IncidentCreateRequest):
    try:
        raised_date = datetime.utcnow()
        logger.info(f"Creating incident for task_id={incident.project_task_id} by user={incident.raised_by}")

        # 1. Get phase_id from project_tasks_list_table
        task_query = (
            select(project_tasks_list_table.c.project_phase_id)
            .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
        )
        task_row = await db.fetch_one(task_query)
        if not task_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": 404, "message": "Project task not found", "data": None}
            )

        v_phase_id = task_row["project_phase_id"]

        # 2. Get project_id from project_phases_list_table
        phase_query = (
            select(project_phases_list_table.c.project_id)
            .where(project_phases_list_table.c.project_phase_id == v_phase_id)
        )
        phase_row = await db.fetch_one(phase_query)
        if not phase_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": 404, "message": "Project phase not found", "data": None}
            )

        v_project_id = phase_row["project_id"]

        # 3. Determine resolved flag
        is_resolved = True if incident.incident_type_id == 1 else False

        # 4. Insert into incident_reports
        insert_stmt = (
            insert(incident_report_table)
            .values(
                project_id=v_project_id,
                phase_id=v_phase_id,
                task_id=incident.project_task_id,
                test_script_name=incident.test_script_name,
                testcase_number=incident.testcase_number,
                failure_type=incident.incident_type_id,
                assigned_to=1, #change it in the further changes
                document=incident.document,
                raise_comment=incident.incident_comment,
                is_resolved=is_resolved,
                raised_by=incident.raised_by,
                raised_date=raised_date,
            )
            .returning(
                incident_report_table.c.incident_report_id,
                incident_report_table.c.project_id,
                incident_report_table.c.phase_id,
                incident_report_table.c.task_id,
                incident_report_table.c.test_script_name,
                incident_report_table.c.testcase_number,
                incident_report_table.c.failure_type,
                incident_report_table.c.assigned_to,
                incident_report_table.c.raise_comment,
                incident_report_table.c.raised_by,
                incident_report_table.c.raised_date,
                incident_report_table.c.is_resolved,
            )
        )
        new_incident = await db.fetch_one(insert_stmt)
        if not new_incident:
            logger.error("Failed to insert incident report")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status_code": 500, "message": "Failed to insert incident report", "data": None}
            )

        logger.info(f"Incident inserted successfully with incident_report_id={new_incident['incident_report_id']}")

        # 5. If SYSTEM ISSUE → update statuses
        if incident.incident_type_id == 2:
            update_task = (
                update(project_tasks_list_table)
                .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
                .values(task_status_id=10, updated_date=datetime.utcnow(), task_users_submitted=0)
            )
            await db.execute(update_task)

            # update_phase = (
            #     update(project_phases_list_table)
            #     .where(project_phases_list_table.c.project_phase_id == v_phase_id)
            #     .values(status_id=10, updated_date=datetime.utcnow())
            # )
            # await db.execute(update_phase)

            # update_project = (
            #     update(projects)
            #     .where(projects.c.project_id == v_project_id)
            #     .values(status_id=10, updated_date=datetime.utcnow())
            # )
            # await db.execute(update_project)
            
             # --- document versioning ---
            latest_doc_query = (
                select(task_docs_table)
                .where(task_docs_table.c.project_task_id == incident.project_task_id)
                .where(task_docs_table.c.is_latest == True)
                # .order_by(task_docs_table.c.created_date.desc())
                .limit(1)
            )
            latest_doc = await db.fetch_one(latest_doc_query)

            if latest_doc:
                
                current_version = float(latest_doc["doc_version"]) if latest_doc["doc_version"] else 0.0
                next_version = current_version + 1.0
                # 1. Update old doc -> mark as not latest
                update_old_doc = (
                    update(task_docs_table)
                    .where(task_docs_table.c.task_doc_id == latest_doc["task_doc_id"])
                    .values(is_latest=False, updated_by=incident.raised_by, updated_date=datetime.utcnow(),doc_version=next_version)
                )
                await db.execute(update_old_doc)

                # 2. Insert new doc with version 1.0
                insert_new_doc = (
                    insert(task_docs_table)
                    .values(
                        project_task_id=incident.project_task_id,
                        project_id=v_project_id,
                        project_phase_id=v_phase_id,
                        document_json=incident.document or "{}",
                        is_latest=True,
                        created_by=incident.raised_by,
                        created_date=datetime.utcnow(),
                        # doc_version=1.0,
                    )
                )
                await db.execute(insert_new_doc)

            logger.info(f"New document created for task_id={incident.project_task_id} with version=1.0") 

            # logger.info("Updated project, phase, and task statuses to Pending (id=4)")

        # 6. Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "Incident reported successfully",
                "data": jsonable_encoder(dict(new_incident))
            }
        )

    except Exception as e:
        logger.exception(f"Error while creating incident report: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": 500, "message": f"An error occurred: {str(e)}", "data": None}
        )      
        

async def resolve_incident_report(db, incident_report_id: int, resolved_by: int, resolve_comment: str):
    try:
        resolved_date = datetime.utcnow()
        logger.info(f"Resolving incident_report_id={incident_report_id} by user={resolved_by}")

        # 1. Fetch incident details
        incident_query = (
            select(
                incident_report_table.c.project_id,
                incident_report_table.c.phase_id,
                incident_report_table.c.task_id
            ).where(incident_report_table.c.incident_report_id == incident_report_id)
        )
        incident_row = await db.fetch_one(incident_query)

        if not incident_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": 404, "message": "Incident not found", "data": None}
            )

        v_project_id = incident_row["project_id"]
        v_phase_id = incident_row["phase_id"]
        v_task_id = incident_row["task_id"]

        # 2. Update incident as resolved
        update_incident = (
            update(incident_report_table)
            .where(incident_report_table.c.incident_report_id == incident_report_id)
            .values(
                is_resolved=True,
                resolved_by=resolved_by,
                resolve_comment=resolve_comment,
                resolved_date=resolved_date
            )
            .returning(
                incident_report_table.c.incident_report_id,
                incident_report_table.c.is_resolved,
                incident_report_table.c.resolved_by,
                incident_report_table.c.resolve_comment,
                incident_report_table.c.resolved_date,
            )
        )
        updated_incident = await db.fetch_one(update_incident)
        if not updated_incident:
            logger.error("Failed to update incident as resolved")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"status_code": 500, "message": "Failed to resolve incident", "data": None}
            )

        # 3. Update related task, phase, and project statuses back to 9
        update_task = (
            update(project_tasks_list_table)
            .where(project_tasks_list_table.c.project_task_id == v_task_id)
            .values(task_status_id=9, updated_date=resolved_date)
        )
        await db.execute(update_task)

        # update_phase = (
        #     update(project_phases_list_table)
        #     .where(project_phases_list_table.c.project_phase_id == v_phase_id)
        #     .values(status_id=9, updated_date=resolved_date)
        # )
        # await db.execute(update_phase)

        # update_project = (
        #     update(projects)
        #     .where(projects.c.project_id == v_project_id)
        #     .values(status_id=9, updated_date=resolved_date)
        # )
        # await db.execute(update_project)

        logger.info(f"Incident {incident_report_id} resolved and statuses restored to 9")

        # 4. Return success response
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "Incident resolved successfully",
                "data": jsonable_encoder(dict(updated_incident))
            }
        )

    except Exception as e:
        logger.exception(f"Error while resolving incident report: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": 500, "message": f"An error occurred: {str(e)}", "data": None}
        )


async def fetch_incident_reports(
    db,
    user_id: Optional[int] = None,
    task_id: Optional[int] = None,
    raised_by: Optional[int] = None,
) -> list[RaiseIncidentOut]:
    try:
        query = (
            select(
                incident_report_table.c.incident_report_id,
                incident_report_table.c.project_id,
                projects.c.project_name,
                incident_report_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                incident_report_table.c.task_id,
                sdlc_tasks_table.c.task_name.label("task_name"),
                incident_report_table.c.test_script_name,
                incident_report_table.c.testcase_number,
                incident_report_table.c.document,
                incident_report_table.c.raise_comment,
                incident_report_table.c.resolve_comment,
                incident_report_table.c.is_resolved,
                incident_report_table.c.raised_by,
                func.to_char(
                    incident_report_table.c.raised_date, 'YYYY-MM-DD"T"HH24:MI:SS'
                ).label("raised_date"),
                incident_report_table.c.resolved_by,
                func.to_char(
                    incident_report_table.c.resolved_date, 'YYYY-MM-DD"T"HH24:MI:SS'
                ).label("resolved_date"),
                case(
                    (incident_report_table.c.failure_type == 1, "Test Case Failure"),
                    else_="System Failure",
                ).label("failure_type"),
                incident_report_table.c.assigned_to,
            )
            .select_from(
                incident_report_table
                .outerjoin(project_phases_list_table, incident_report_table.c.phase_id == project_phases_list_table.c.project_phase_id)
                .outerjoin(projects, incident_report_table.c.project_id == projects.c.project_id)
                .outerjoin(sdlc_phases_table, project_phases_list_table.c.project_phase_id == sdlc_phases_table.c.phase_id)
                .outerjoin(project_tasks_list_table, incident_report_table.c.task_id == project_tasks_list_table.c.project_task_id)
                .outerjoin(sdlc_tasks_table, project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id)
            )
            .where(
                and_(
                    incident_report_table.c.assigned_to == user_id if user_id is not None else True,
                    incident_report_table.c.task_id == task_id if task_id is not None else True,
                    incident_report_table.c.raised_by == raised_by if raised_by is not None else True,
                    incident_report_table.c.failure_type == 2,  # System issues only
                )
            )
            .order_by(
                incident_report_table.c.incident_report_id.desc(),
                incident_report_table.c.raised_date.desc(),
            )
        )

        rows = await db.fetch_all(query)
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["raised_date"] = row_dict["raised_date"] or None
            row_dict["resolved_date"] = row_dict["resolved_date"] or None
            result.append(RaiseIncidentOut(**row_dict))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Incident reports fetched successfully",
                "data": result,
            }),
        )

    except Exception as e:
        logger.exception(f"Error while fetching incident reports: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "details": str(e),
                "data": None,
            },
        )



# async def get_incident_reports(user_id: int, project_id: int):
#     try:
#         logger.info(f"Fetching incident reports for user_id={user_id}, project_id={project_id}")

#         query = (
#             select(
#                 incident_report_table.c.incident_report_id,
#                 incident_report_table.c.project_id,  # Added project_id
#                 incident_report_table.c.phase_id.label("project_phase_id"),
#                 projects.c.project_name,  # Added project_name
#                 sdlc_phases_table.c.phase_name,
#                 incident_report_table.c.raise_comment,
#                 incident_report_table.c.raised_date,
#                 incident_report_table.c.resolve_comment,
#                 incident_report_table.c.resolved_date,
#                 incident_report_table.c.is_resolved,
#                 incident_report_table.c.assigned_to,
#                 incident_report_table.c.raised_by,
#                 incident_report_table.c.resolved_by,

#             )
#             .join(
#                 project_phases_list_table,
#                 incident_report_table.c.phase_id == project_phases_list_table.c.project_phase_id,
#                 isouter=True
#             )
#             .join(
#                 sdlc_phases_table,
#                 project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id,
#                 isouter=True
#             )
#             .join(
#                 projects,
#                 incident_report_table.c.project_id == projects.c.project_id,
#                 isouter=True
#             )
#             # Filter for raised_by or resolved_by matching user_id and failure_type = 2
#             .where(
#                 and_(
#                     or_(
#                         incident_report_table.c.raised_by == user_id,
#                         incident_report_table.c.resolved_by == user_id
#                     ),
#                     incident_report_table.c.failure_type == 2
#                 )
#             )
#         )

#         # Filter by project_id only if non-zero
#         if project_id != 0:
#             query = query.where(incident_report_table.c.project_id == project_id)

#         results = await database.fetch_all(query)

#         if not results:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": "No incident reports found",
#                     "data": [],
#                 },
#             )

#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content=jsonable_encoder({
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Incident reports fetched successfully",
#                 "data": [dict(r) for r in results],
#             }),
#         )

#     except Exception as e:
#         logger.exception(f"Error fetching incident reports: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": "Internal server error",
#                 "data": None,
#             },
#         )
        
    

async def get_task_incident_reports(task_id: int):
    try:
        logger.info(f"Fetching incident reports for task_id={task_id}")

        query = (
            select(
                incident_report_table.c.incident_report_id,
                incident_report_table.c.project_id,  # Added project_id
                incident_report_table.c.phase_id.label("project_phase_id"),
                projects.c.project_name,  # Added project_name
                sdlc_phases_table.c.phase_name,
                sdlc_phases_table.c.phase_code,
                incident_report_table.c.raise_comment,
                incident_report_table.c.raised_date,
                incident_report_table.c.resolve_comment,
                incident_report_table.c.resolved_date,
                incident_report_table.c.is_resolved,
                incident_report_table.c.assigned_to,
                incident_report_table.c.raised_by,
                incident_report_table.c.resolved_by,

            )
            .join(
                project_phases_list_table,
                incident_report_table.c.phase_id == project_phases_list_table.c.project_phase_id,
                isouter=True
            )
            .join(
                sdlc_phases_table,
                project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id,
                isouter=True
            )
            .join(
                projects,
                incident_report_table.c.project_id == projects.c.project_id,
                isouter=True
            )
            # Filter for raised_by or resolved_by matching user_id and failure_type = 2
            .where(
                and_(
                    
                        incident_report_table.c.task_id == task_id,
                    ),
                    incident_report_table.c.failure_type == 2
                
            )
        )

        results = await database.fetch_all(query)

        if not results:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No incident reports found",
                    "data": [],
                },
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder({
                "status_code": status.HTTP_200_OK,
                "message": "Incident reports fetched successfully",
                "data": [dict(r) for r in results],
            }),
        )

    except Exception as e:
        logger.exception(f"Error fetching incident reports: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )
        
        
    
# async def raise_incident_report(db, incident: IncidentCreateRequest):
#     try:
#         raised_date = datetime.utcnow()
#         logger.info(f"Creating incident for task_id={incident.project_task_id} by user={incident.raised_by}")

#         # 1. Get phase_id from project_tasks_list_table
#         task_query = (
#             select(project_tasks_list_table.c.project_phase_id)
#             .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
#         )
#         task_row = await db.fetch_one(task_query)
#         if not task_row:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={"status_code": 404, "message": "Project task not found", "data": None}
#             )

#         v_phase_id = task_row["project_phase_id"]

#         # 2. Get project_id from project_phases_list_table
#         phase_query = (
#             select(project_phases_list_table.c.project_id)
#             .where(project_phases_list_table.c.project_phase_id == v_phase_id)
#         )
#         phase_row = await db.fetch_one(phase_query)
#         if not phase_row:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={"status_code": 404, "message": "Project phase not found", "data": None}
#             )

#         v_project_id = phase_row["project_id"]

#         # 3. Insert into incident_reports
#         insert_stmt = (
#             insert(incident_reports_table)
#             .values(
#                 project_id=v_project_id,
#                 phase_id=v_phase_id,
#                 task_id=incident.project_task_id,
#                 raised_by=incident.raised_by,
#                 raised_date=raised_date,
#                 is_resolved=False,
#             )
#             .returning(
#                 incident_reports_table.c.incident_report_id,
#             )
#         )
#         incident_report_id = await db.fetch_one(insert_stmt)
        
#         query = insert(json_template_transactions).values(
#             created_by=incident.raised_by,
#             template_json=incident.document,
#             created_date=datetime.utcnow(),
#         )
#         record_id = await database.execute(query)
        
        
#         query = insert(incident_report_transactions).values(
#             incident_report_id=
#             role_id=
#             status=
#             created_date=
#             is_resolved=true
#         )
        
        
#         if not incident_report_id:
#             logger.error("Failed to insert incident report")
#             return JSONResponse(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 content={"status_code": 500, "message": "Failed to insert incident report", "data": None}
#             )

#         logger.info(f"Incident inserted successfully with incident_report_id={incident_report_id['incident_report_id']}")

#         # 5. If SYSTEM ISSUE → update statuses
#         # if incident.incident_type_id == 2:
#         update_task = (
#             update(project_tasks_list_table)
#             .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
#             .values(task_status_id=10, updated_date=datetime.utcnow(), task_users_submitted=0)
#         )
#         await db.execute(update_task)

#         # update_phase = (
#         #     update(project_phases_list_table)
#         #     .where(project_phases_list_table.c.project_phase_id == v_phase_id)
#         #     .values(status_id=10, updated_date=datetime.utcnow())
#         # )
#         # await db.execute(update_phase)

#         # update_project = (
#         #     update(projects)
#         #     .where(projects.c.project_id == v_project_id)
#         #     .values(status_id=10, updated_date=datetime.utcnow())
#         # )
#         # await db.execute(update_project)
        
#             # --- document versioning ---
#         latest_doc_query = (
#             select(task_docs_table)
#             .where(task_docs_table.c.project_task_id == incident.project_task_id)
#             .where(task_docs_table.c.is_latest == True)
#             # .order_by(task_docs_table.c.created_date.desc())
#             .limit(1)
#         )
#         latest_doc = await db.fetch_one(latest_doc_query)

#         if latest_doc:
            
#             current_version = float(latest_doc["doc_version"]) if latest_doc["doc_version"] else 0.0
#             next_version = current_version + 1.0
#             # 1. Update old doc -> mark as not latest
#             update_old_doc = (
#                 update(task_docs_table)
#                 .where(task_docs_table.c.task_doc_id == latest_doc["task_doc_id"])
#                 .values(is_latest=False, updated_by=incident.raised_by, updated_date=datetime.utcnow(),doc_version=next_version)
#             )
#             await db.execute(update_old_doc)

#             # 2. Insert new doc with version 1.0
#             insert_new_doc = (
#                 insert(task_docs_table)
#                 .values(
#                     project_task_id=incident.project_task_id,
#                     project_id=v_project_id,
#                     project_phase_id=v_phase_id,
#                     document_json=incident.document or "{}",
#                     is_latest=True,
#                     created_by=incident.raised_by,
#                     created_date=datetime.utcnow(),
#                     # doc_version=1.0,
#                 )
#             )
#             await db.execute(insert_new_doc)

#             logger.info(f"New document created for task_id={incident.project_task_id} with version=1.0") 

#             # logger.info("Updated project, phase, and task statuses to Pending (id=4)")

#         # 6. Return success response
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status_code": 200,
#                 "message": "Incident reported successfully",
#                 "data": jsonable_encoder(dict(incident_report_id))
#             }
#         )

#     except Exception as e:
#         logger.exception(f"Error while creating incident report: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"status_code": 500, "message": f"An error occurred: {str(e)}", "data": None}
#         )      
  

async def raise_incident_report(db, incident):
    try:
        raised_date = datetime.utcnow()
        logger.info(f"Processing incident for task_id={incident.project_task_id} by user={incident.raised_by}")

        # 1) fetch phase_id from task, then project_id
        task_row = await db.fetch_one(
            select(project_tasks_list_table.c.project_phase_id)
            .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
        )
        if not task_row:
            return JSONResponse(status_code=404, content={"message": "Project task not found"})

        v_phase_id = task_row["project_phase_id"]

        phase_row = await db.fetch_one(
            select(project_phases_list_table.c.project_id)
            .where(project_phases_list_table.c.project_phase_id == v_phase_id)
        )
        if not phase_row:
            return JSONResponse(status_code=404, content={"message": "Project phase not found"})

        v_project_id = phase_row["project_id"]

        # 2) create incident if new
        is_new_incident = not incident.incident_report_id or incident.incident_report_id == 0

        if is_new_incident:
            res = await db.fetch_one(
                insert(incident_reports_table)
                .values(
                    project_id=v_project_id,
                    phase_id=v_phase_id,
                    task_id=incident.project_task_id,
                    raised_by=incident.raised_by,
                    raised_date=raised_date,
                    is_resolved=False,
                )
                .returning(incident_reports_table.c.incident_report_id)
            )
            incident_report_id = res["incident_report_id"]
            logger.info(f"New incident created: ID={incident_report_id}")

            # your task status update on new incident
            await db.execute(
                update(project_tasks_list_table)
                .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
                .values(task_status_id=10, updated_date=datetime.utcnow(), task_users_submitted=0)
            )
        else:
            incident_report_id = incident.incident_report_id
            logger.info(f"Continuing existing incident: ID={incident_report_id}")

        # 3) get current user's role
        current_role_id = await get_user_role(incident.raised_by, db)
        if not current_role_id:
            return JSONResponse(status_code=400, content={"message": "User role not found"})

        # 4) insert JSON snapshot (always insert new snapshot per submission)
        json_row = await db.fetch_one(
            insert(json_template_transactions)
            .values(
                created_by=incident.raised_by,
                template_json=incident.document,
                created_date=datetime.utcnow(),
            )
            .returning(json_template_transactions.c.transaction_template_id)
        )
        json_transaction_id = json_row["transaction_template_id"]
        logger.info(f"Inserted JSON transaction_id={json_transaction_id}")

        # 5) workflow handling
        if is_new_incident:
            # Insert current user's submitted transaction
            await db.execute(
                insert(incident_report_transactions).values(
                    incident_report_id=incident_report_id,
                    transaction_template_id=json_transaction_id,
                    role_id=current_role_id,
                    status=3,  # submitted
                    created_date=datetime.utcnow(),
                )
            )

            # Insert next role pending (use same json snapshot so next user sees the context)
            next_role_id = await get_next_role(current_role_id)
            if next_role_id:
                await db.execute(
                    insert(incident_report_transactions).values(
                        incident_report_id=incident_report_id,
                        transaction_template_id=json_transaction_id,
                        role_id=next_role_id,
                        status=1,  # pending
                        created_date=datetime.utcnow(),
                    )
                )

        else:
            # existing incident: update the latest pending row for current role -> submitted
            pending_row = await db.fetch_one(
                select(incident_report_transactions.c.incident_report_transaction_id)
                .where(incident_report_transactions.c.incident_report_id == incident_report_id)
                .where(incident_report_transactions.c.role_id == current_role_id)
                .where(incident_report_transactions.c.status == 1)  # pending
                .order_by(incident_report_transactions.c.created_date.desc())
                .limit(1)
            )

            if pending_row:
                await db.execute(
                    update(incident_report_transactions)
                    .where(incident_report_transactions.c.incident_report_transaction_id == pending_row["incident_report_transaction_id"])
                    .values(
                        status=3,  # submitted
                        transaction_template_id=json_transaction_id,
                        created_date=datetime.utcnow(),
                    )
                )
            else:
                # defensive: if no pending found, insert a submitted record for audit
                await db.execute(
                    insert(incident_report_transactions).values(
                        incident_report_id=incident_report_id,
                        transaction_template_id=json_transaction_id,
                        role_id=current_role_id,
                        status=3,
                        created_date=datetime.utcnow(),
                    )
                )

            # insert next role pending (with the same json snapshot)
            next_role_id = await get_next_role(current_role_id)
            
            
            if next_role_id:
                # ensure we don't create duplicate pending for same role (optional safety)
                existing_next = await db.fetch_one(
                    select(incident_report_transactions.c.incident_report_transaction_id)
                    .where(incident_report_transactions.c.incident_report_id == incident_report_id)
                    .where(incident_report_transactions.c.role_id == next_role_id)
                    .where(incident_report_transactions.c.status == 1)
                    .limit(1)
                )
                if not existing_next:
                    await db.execute(
                        insert(incident_report_transactions).values(
                            incident_report_id=incident_report_id,
                            transaction_template_id=json_transaction_id,
                            role_id=next_role_id,
                            status=1,  # pending
                            created_date=datetime.utcnow(),
                        )
                    )
                
            else:
                await db.execute(
                    update(incident_reports_table)
                    .where(incident_reports_table.c.incident_report_id == incident_report_id)
                    .values(is_resolved=True)
                )

                # Set task back to active (id=1)
                await db.execute(
                    update(project_tasks_list_table)
                    .where(project_tasks_list_table.c.project_task_id == incident.project_task_id)
                    .values(task_status_id=1, updated_date=datetime.utcnow())
                )

                logger.info("Incident fully completed and task set to Active")
                # await db.commit()

                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Incident completed by Sign Off",
                        "incident_report_id": incident_report_id,
                    }
                )

        return JSONResponse(
            status_code=200,
            content={
                "message": "Incident processed successfully",
                "incident_report_id": incident_report_id,
                "json_transaction_id": json_transaction_id,
            },
        )

    except Exception as e:
        logger.exception(f"Error in raise_incident_report: {str(e)}")
        # await db.rollback()
        return JSONResponse(status_code=500, content={"message": f"Error: {str(e)}"})


# utility: fetch single role for the user
async def get_user_role(user_id: int, db):
    q = (
        select(user_role_mapping_table.c.role_id)
        .where(and_(user_role_mapping_table.c.user_id == user_id, user_role_mapping_table.c.is_active == True))
        .limit(1)
    )
    row = await db.fetch_one(q)
    return row["role_id"] if row else None

async def get_next_role(current_role_id: int):
    workflow = {
        8: 6,   
        6: 7,   
        7: 9,   
        9: None 
    }
    return workflow.get(current_role_id)


async def get_incident_reports(db, user_id: int | None = None, project_id: int | None = None):
    try:
        query = """
            SELECT * 
            FROM ai_verify_transaction.get_incidents(
                p_user_id := :user_id,
                p_project_id := :project_id
            );
        """

        rows = await db.fetch_all(query, values={
            "user_id": user_id,
            "project_id": project_id
        })
        print('fetching data for user - service file ${user_id}')

        return {
            "status_code": 200,
            "message": "Incident reports fetched successfully",
            "count": len(rows),
            "data": [dict(r) for r in rows]
        }


    except Exception as e:
        logger.exception(f"Error fetching incidents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": f"Error: {str(e)}"}
        )


