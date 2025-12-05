import os
import aiofiles
import logging
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,and_, update, insert, func, or_
from fastapi.responses import JSONResponse
from app.db.transaction.project_comments import project_comments_table
from app.db.master.equipment_ai_docs import equipment_ai_docs_table
from app.db.master.equipment import equipment_list_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.docs.task_docs import task_docs_table
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.projects import projects
from app.db.transaction.users import users
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.transaction.project_task_users import project_task_users_table
from fastapi import status
from datetime import datetime
from dotenv import load_dotenv
from app.db.transaction.project_files import project_files_table
from app.schemas.docs.task_docs_schema import ProjectFileItem, taskDocumentsResponse
from app.db.master.sdlc_tasks import sdlc_tasks_table

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()
EQUIP_DOCS_PATH = os.getenv("EQUIP_DOCS_PATH")

async def get_document_by_project_task_id_service(db, project_task_id: int):
    try:
        logger.info(f"Fetching document for project_task_id: {project_task_id}")

        # Bad Request condition
        if not project_task_id:
            logger.warning("Project Task ID is missing in request.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "project_task_id is required",
                    "data": {}
                }
            )

        print('first - if passed--')
        #  Step 1: Check in task_docs (latest version)
        query_task_doc = select(task_docs_table).where(
            and_(
                task_docs_table.c.project_task_id == project_task_id,
                task_docs_table.c.is_latest == True
            )
        )
        task_doc = await db.fetch_one(query_task_doc)

        if task_doc:
            logger.info(f"Found latest task document for project_task_id {project_task_id}.")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Task document fetched successfully",
                    "data": {
                        "project_task_id": project_task_id,
                        "file_flag": 2,
                        "task_document": task_doc.document_json
                    }
                }
            )

        #  Step 2: Fallback - derive from equipment_ai_docs
        # 2.1 Get project_phase_id from project_tasks_list
        query_phase = select(project_tasks_list_table.c.project_phase_id).where(
            project_tasks_list_table.c.project_task_id == project_task_id
        )
        project_phase = await db.fetch_one(query_phase)
        if not project_phase:
            logger.warning(f"No project_phase_id found for project_task_id {project_task_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No project_phase_id found for project_task_id {project_task_id}",
                    "data": {}
                }
            )
        print('second - if passed--')

        # Step 2.2: Check task_docs by project_phase_id (latest record)
        query_task_docs_by_phase = (
            select(task_docs_table)
            .where(task_docs_table.c.project_phase_id == project_phase.project_phase_id)
            .order_by(task_docs_table.c.task_doc_id.desc())
            .limit(1)
        )
        
        phase_task_doc = await db.fetch_one(query_task_docs_by_phase)

        if phase_task_doc:
            logger.info(f"Found task document for project_phase_id {project_phase.project_phase_id}.")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Task document fetched successfully using project_phase_id",
                    "data": {
                        "project_task_id": project_task_id,
                        "file_flag": 2,
                        "task_document": phase_task_doc.document_json
                    }
                }
            )

        # 2.2 Get project_id, phase_id from project_phases_list
        query_proj_phase = select(
            project_phases_list_table.c.project_id,
            project_phases_list_table.c.phase_id
        ).where(project_phases_list_table.c.project_phase_id == project_phase.project_phase_id)
        proj_phase = await db.fetch_one(query_proj_phase)
        if not proj_phase:
            logger.warning(f"No project_id/phase_id found for project_phase_id {project_phase.project_phase_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No project_id/phase_id found for project_phase_id {project_phase.project_phase_id}",
                    "data": {}
                }
            )

        # 2.3 Get equipment_id from projects
        query_proj = select(projects.c.equipment_id).where(
            projects.c.project_id == proj_phase.project_id
        )
        project = await db.fetch_one(query_proj)
        if not project:
            logger.warning(f"No equipment_id found for project_id {proj_phase.project_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No equipment_id found for project_id {proj_phase.project_id}",
                    "data": {}
                }
            )
        # --------------------------------------------------------------------
        # # 2.4 Get document_json from equipment_ai_docs
        # query_equip_doc = select(equipment_ai_docs_table.c.document_json).where(
        #     and_(
        #         equipment_ai_docs_table.c.equipment_id == project.equipment_id,
        #         equipment_ai_docs_table.c.phase_id == proj_phase.phase_id
        #     )
        # )
        # equip_doc = await db.fetch_one(query_equip_doc)
        #
        # if equip_doc:
        #     logger.info(f"Found fallback document from equipment_ai_docs for project_task_id {project_task_id}.")
        #     return JSONResponse(
        #         status_code=status.HTTP_200_OK,
        #         content={
        #             "status_code": status.HTTP_200_OK,
        #             "message": "Task document fetched successfully from equipment AI docs",
        #             "data": {
        #                 "project_task_id": project_task_id,
        #                 "file_flag": 1,
        #                 "task_document": equip_doc.document_json
        #             }
        #         }
        #     )
        #
        # # 2.5 Nothing found in fallback either
        # logger.warning(f"No equipment_ai_docs record found for equipment_id {project.equipment_id} and phase_id {proj_phase.phase_id}.")
        # return JSONResponse(
        #     status_code=status.HTTP_404_NOT_FOUND,
        #     content={
        #         "status_code": status.HTTP_404_NOT_FOUND,
        #         "message": f"No equipment_ai_docs found for equipment_id {project.equipment_id} and phase_id {proj_phase.phase_id}",
        #         "data": {}
        #     }
        # )
        # --------------------------------------------------------------------------------
        # Step 2.4: Get document from folder path
        # Get equipment_code from equipment_list
        query_equipment_code = select(equipment_list_table.c.equipment_code).where(
            equipment_list_table.c.equipment_id == project.equipment_id
        )
        equipment = await db.fetch_one(query_equipment_code)

        if not equipment:
            logger.warning(f"No equipment_code found for equipment_id {project.equipment_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No equipment_code found for equipment_id {project.equipment_id}",
                    "data": {}
                }
            )

        # Step 2.5: Get phase_code from sdlc_phases
        query_phase_code = select(sdlc_phases_table.c.phase_code).where(
            sdlc_phases_table.c.phase_id == proj_phase.phase_id
        )
        phase = await db.fetch_one(query_phase_code)

        if not phase:
            logger.warning(f"No phase_code found for phase_id {proj_phase.phase_id}.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": f"No phase_code found for phase_id {proj_phase.phase_id}",
                    "data": {}
                }
            )
        # file_name = f"{project.equipment_id}_{proj_phase.phase_id}.md"
        file_name = f"{equipment.equipment_code}_{phase.phase_code}.md"
        # file_name = "BOX_Application_IQ.md"
        file_path = os.path.join(EQUIP_DOCS_PATH, file_name)

        if os.path.exists(file_path):
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                file_content = await f.read()

            logger.info(f"Found fallback document from folder path for equipment_code {equipment.equipment_code} and phase_code {phase.phase_code}.")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Task document fetched successfully from folder path",
                    "data": {
                        "project_task_id": project_task_id,
                        "file_flag": 1,
                        "task_document": file_content
                    }
                }
            )

        logger.warning(f"No .md file found in file path for equipment_code {equipment.equipment_code} and phase_code {phase.phase_code}.")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": f"No .md file found for folder path",
                "data": {}
            }
        )
    # ----------------------------------------------------------------------------------

    except Exception as e:
        logger.error(f"Internal server error while fetching document for project_task_id {project_task_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {}
            }
        )


# async def save_project_task_document_service(db, payload):
#     try:
#         if not payload.project_task_id or not payload.document_json or not payload.created_by:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "message": "project_task_id, document_json, and created_by are required",
#                     "data": None,
#                 },
#             )
#
#         # Check if record exists with project_task_id and is_latest = true
#         query = select(task_docs_table).where(
#             task_docs_table.c.project_task_id == payload.project_task_id,
#             task_docs_table.c.is_latest == True
#         )
#         existing_doc = await db.fetch_one(query)
#
#         if existing_doc:
#             # Update document_json of existing record
#             upd_query = (
#                 update(task_docs_table)
#                 .where(task_docs_table.c.task_doc_id == existing_doc.task_doc_id)
#                 .values(document_json=payload.document_json)
#             )
#             await db.execute(upd_query)
#
#             return JSONResponse(
#                 status_code=status.HTTP_200_OK,
#                 content={
#                     "status_code": status.HTTP_200_OK,
#                     "message": "Document updated successfully",
#                     "data": {"task_doc_id": existing_doc.task_doc_id},
#                 },
#             )
#         else:
#             # Insert new document with version = 1
#             ins_query = (
#                 insert(task_docs_table)
#                 .values(
#                     project_task_id=payload.project_task_id,
#                     document_json=payload.document_json,
#                     is_latest=True,
#                     created_by=payload.created_by,
#                     created_date=datetime.utcnow(),
#                     doc_version=1,
#                 )
#                 .returning(task_docs_table.c.task_doc_id)
#             )
#             new_id = await db.execute(ins_query)
#
#             return JSONResponse(
#                 status_code=status.HTTP_201_CREATED,
#                 content={
#                     "status_code": status.HTTP_201_CREATED,
#                     "message": "Document created successfully",
#                     "data": {"task_doc_id": new_id},
#                 },
#             )
#
#     except Exception as e:
#         logger.error(f"Error saving project task document: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": f"Internal server error: {str(e)}",
#                 "data": None,
#             },
#         )

async def save_project_task_document_service(db, payload):
    try:
        logger.info("Starting save_project_task_document_service")
        if not payload.project_task_id or not payload.document_json or not payload.created_by:
            logger.warning("Missing required fields: project_task_id, document_json, or created_by")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Fields are required",
                    "data": None,
                },
            )

        # Fetch project_phase_id from project_tasks_list
        query_task = select(project_tasks_list_table.c.project_phase_id).where(
            project_tasks_list_table.c.project_task_id == payload.project_task_id
        )
        task_result = await db.fetch_one(query_task)
        if not task_result:
            logger.error(f"Task ID: {payload.project_task_id} not found in project_tasks_list")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Task not found",
                    "data": None,
                },
            )
        project_phase_id = task_result["project_phase_id"]
        logger.info(f"Fetched project_phase_id: {project_phase_id} for task_id: {payload.project_task_id}")

        # Fetch project_id from project_phases_list
        query_phase = select(project_phases_list_table.c.project_id).where(
            project_phases_list_table.c.project_phase_id == project_phase_id
        )
        phase_result = await db.fetch_one(query_phase)
        if not phase_result:
            logger.error(f"Phase ID: {project_phase_id} not found in project_phases_list")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project phase not found",
                    "data": None,
                },
            )
        project_id = phase_result["project_id"]
        logger.info(f"Fetched project_id: {project_id} for project_phase_id: {project_phase_id}")

        # Check if record exists with project_task_id and is_latest = true
        query = select(task_docs_table).where(
            task_docs_table.c.project_task_id == payload.project_task_id,
            task_docs_table.c.is_latest == True
        )
        existing_doc = await db.fetch_one(query)

        if not existing_doc:
            # Case 1: project_task_id not exist → create new record
            ins_query = (
                insert(task_docs_table)
                .values(
                    project_task_id=payload.project_task_id,
                    project_id=project_id,
                    project_phase_id=project_phase_id,
                    document_json=payload.document_json,
                    is_latest=True,
                    created_by=payload.created_by,
                    created_date=datetime.utcnow(),
                )
                .returning(task_docs_table.c.task_doc_id)
            )
            new_id = await db.execute(ins_query)
            logger.info(f"New document created with task_doc_id={new_id}")
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": "Document created successfully",
                    "data": None,
                },
            )

        # Case 2: project_task_id exists and doc_version is NULL and is_latest = true
        if existing_doc.doc_version is None:
            upd_query = (
                update(task_docs_table)
                .where(task_docs_table.c.task_doc_id == existing_doc.task_doc_id)
                .values(
                    document_json=payload.document_json,
                    updated_by=payload.created_by,
                    updated_date=datetime.utcnow()
                )
            )
            await db.execute(upd_query)
            logger.info(f"Document updated successfully for task_doc_id={existing_doc.task_doc_id}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status_code": status.HTTP_200_OK,
                    "message": "Document updated successfully",
                    "data": None,
                },
            )

        # Case 3: project_task_id exists and doc_version is NOT NULL and is_latest = true
        else:
            # Mark all existing docs as not latest
            upd_old = (
                update(task_docs_table)
                .where(task_docs_table.c.project_task_id == payload.project_task_id)
                .values(is_latest=False)
            )
            await db.execute(upd_old)

            ins_query = (
                insert(task_docs_table)
                .values(
                    project_task_id=payload.project_task_id,
                    document_json=payload.document_json,
                    is_latest=True,
                    project_id=project_id,
                    project_phase_id=project_phase_id,
                    created_by=payload.created_by,
                    created_date=datetime.utcnow(),
                )
                .returning(task_docs_table.c.task_doc_id)
            )
            new_id = await db.execute(ins_query)
            logger.info(f"New document version created with task_doc_id={new_id}")
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": "document saved successfully",
                    "data": None,
                },
            )

    except Exception as e:
        logger.error(f"Error saving project task document: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": None,
            },
        )


# async def submit_project_task_document_service(db, payload):
#     try:
#         if not payload.project_task_id or not payload.document_json or not payload.created_by:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "All parameters are required"}
#             )
#
#         # Fetch existing documents for given project_task_id
#         query = select(task_docs_table).where(task_docs_table.c.project_task_id == payload.project_task_id)
#         existing_docs = await db.fetch_all(query)
#
#         if existing_docs:
#             # Get latest version number
#             latest_version = max([float(doc["doc_version"]) for doc in existing_docs])
#
#             # Mark existing docs as not latest
#             await db.execute(
#                 update(task_docs_table)
#                 .where(task_docs_table.c.project_task_id == payload.project_task_id)
#                 .values(is_latest=False)
#             )
#
#             # Insert new document with version +1
#             new_doc = {
#                 "project_task_id": payload.project_task_id,
#                 "document_json": payload.document_json,
#                 "is_latest": True,
#                 "created_by": payload.created_by,
#                 "created_date": datetime.utcnow(),
#                 "doc_version": latest_version + 1,
#             }
#             new_id = await db.execute(task_docs_table.insert().values(new_doc))
#             return {
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Document submitted successfully (new version created)",
#                 "data": {"task_doc_id": new_id, "doc_version": latest_version + 1}
#             }
#
#         else:
#             # Insert first version
#             new_doc = {
#                 "project_task_id": payload.project_task_id,
#                 "document_json": payload.document_json,
#                 "is_latest": True,
#                 "created_by": payload.created_by,
#                 "created_date": datetime.utcnow(),
#                 "doc_version": 1,
#             }
#             new_id = await db.execute(task_docs_table.insert().values(new_doc))
#             return {
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Document submitted successfully (first version created)",
#                 "data": {"task_doc_id": new_id, "doc_version": 1}
#             }
#
#     except Exception as e:
#         logger.error(f"Error in submit_project_task_document_service: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={"status_code": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": "Internal Server Error"}
#         )

# async def submit_project_task_document_service(db, payload):
#     try:
#         logger.info("submit_project_task_document_service api execution started")
#         # Validate required parameters
#         if not all([payload.project_task_id, payload.document_json, payload.task_status_id, payload.updated_by]):
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "message": "All parameters are required",
#                     "data": None
#                 }
#             )
#
#         # Get current task details
#         query_task = select(
#             project_tasks_list_table.c.task_status_id,
#             project_tasks_list_table.c.project_phase_id,
#             project_tasks_list_table.c.task_users_count,
#             project_tasks_list_table.c.task_users_submitted
#         ).where(project_tasks_list_table.c.project_task_id == payload.project_task_id)
#         task_result = await db.fetch_one(query_task)
#         if not task_result:
#             logger.error(f"Task ID: {payload.project_task_id} not found")
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": "Task not found",
#                     "data": None
#                 }
#             )
#
#         current_status = task_result["task_status_id"]
#         phase_id = task_result["project_phase_id"]
#         task_users_count = task_result["task_users_count"]
#         task_users_submitted = task_result["task_users_submitted"] or 0
#         logger.info(
#             f"Fetched task details - Task ID: {payload.project_task_id}, Status: {current_status}, "
#             f"Phase ID: {phase_id}, Users Count: {task_users_count}, Submitted Count: {task_users_submitted}"
#         )
#
#         # Get project ID
#         query_project = select(project_phases_list_table.c.project_id).where(
#             project_phases_list_table.c.project_phase_id == phase_id
#         )
#         project_result = await db.fetch_one(query_project)
#         if not project_result:
#             logger.error(f"Phase ID: {phase_id} not found")
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": "Project phase not found",
#                     "data": None
#                 }
#             )
#         project_id = project_result["project_id"]
#         logger.info(f"Fetched Project ID: {project_id} for Phase ID: {phase_id}")
#
#         # Check unresolved comments
#         query_comments = select(func.count()).select_from(
#             project_comments_table.join(
#                 project_tasks_list_table,
#                 project_tasks_list_table.c.project_task_id == project_comments_table.c.project_task_id
#             )
#         ).where(
#             and_(
#                 project_comments_table.c.is_resolved == False,
#                 or_(
#                     project_tasks_list_table.c.project_phase_id == phase_id,
#                     project_tasks_list_table.c.project_task_id == payload.project_task_id + 1
#                 )
#             )
#         )
#         unresolved_comments = await db.fetch_val(query_comments)
#         logger.info(f"Fetched unresolved comments: {unresolved_comments}")
#         if unresolved_comments > 0:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "message": "You have comments to resolve before submitting task",
#                     "data": None
#                 }
#             )
#
#         # Verify user and role
#         query_user = select(users.c.user_name, user_role_mapping_table.c.role_id).select_from(
#             users.join(user_role_mapping_table, users.c.user_id == user_role_mapping_table.c.user_id)
#         ).where(users.c.user_id == payload.updated_by)
#         user_result = await db.fetch_one(query_user)
#         if not user_result:
#             logger.error(f"User ID: {payload.updated_by} not found or has no role")
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": status.HTTP_404_NOT_FOUND,
#                     "message": "User not found or has no role",
#                     "data": None
#                 }
#             )
#         user_name = user_result["user_name"]
#         role_id = user_result["role_id"]
#         logger.info(f"Fetched user details - User Name: {user_name}, Role ID: {role_id} for User ID: {payload.updated_by}")
#
#         # Check if task status is unchanged
#         if current_status == payload.task_status_id:
#             logger.info(f"Status unchanged - Current Status: {current_status} matches Input Status: {payload.task_status_id}")
#             return {
#                 "status_code": status.HTTP_200_OK,
#                 "message": f"Task submitted by: {user_name}",
#                 "data": {}
#             }
#
#         # Check if user is assigned and hasn't submitted
#         query_user_task = select(project_task_users_table.c.submitted).where(
#             and_(
#                 project_task_users_table.c.project_task_id == payload.project_task_id,
#                 project_task_users_table.c.user_id == payload.updated_by
#             )
#         )
#         user_task_result = await db.fetch_one(query_user_task)
#         if not user_task_result:
#             logger.error(f"User ID: {payload.updated_by} not assigned to Task ID: {payload.project_task_id}")
#             return JSONResponse(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 content={
#                     "status_code": status.HTTP_403_FORBIDDEN,
#                     "message": "User not assigned to this task",
#                     "data": None
#                 }
#             )
#         if user_task_result["submitted"]:
#             logger.info(f"User already submitted - User ID: {payload.updated_by} for Task ID: {payload.project_task_id}")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "message": "You have already submitted this task",
#                     "data": None
#                 }
#             )
#         logger.info(f"User has not submitted yet - User ID: {payload.updated_by} for Task ID: {payload.project_task_id}")
#
#         # Increment submitted count
#         task_users_submitted += 1
#         logger.info(f"Incremented submitted count to: {task_users_submitted} for Task ID: {payload.project_task_id}")
#
#         # Check if document exists
#         query_doc = select(task_docs_table.c.doc_version).where(task_docs_table.c.project_task_id == payload.project_task_id)
#         doc_result = await db.fetch_one(query_doc)
#         doc_version = float(doc_result["doc_version"]) if doc_result else 0.0
#         logger.info(f"Fetched doc version: {doc_version} for Task ID: {payload.project_task_id}")
#
#         if not doc_result:
#             # Insert first document
#             logger.info(f"No document exists for Task ID: {payload.project_task_id}, inserting new doc with version 1.0")
#             new_doc = {
#                 "project_task_id": payload.project_task_id,
#                 "project_phase_id": phase_id,
#                 "project_id": project_id,
#                 "document_json": payload.document_json,
#                 "doc_version": 1.0,
#                 "created_by": payload.updated_by,
#                 "submitted_by": payload.updated_by,
#                 "created_date": datetime.utcnow(),
#                 "is_latest": True
#             }
#             new_id = await db.execute(task_docs_table.insert().values(new_doc))
#         else:
#             if doc_version is None or doc_version == 0.0:
#                 # Update document to version 1.0
#                 logger.info(f"Document exists with version 0.0 for Task ID: {payload.project_task_id}, updating to version 1.0")
#                 await db.execute(
#                     update(task_docs_table)
#                     .where(task_docs_table.c.project_task_id == payload.project_task_id)
#                     .values(
#                         doc_version=1.0,
#                         document_json=payload.document_json,
#                         updated_by=payload.updated_by,
#                         submitted_by=payload.updated_by,
#                         updated_date=datetime.utcnow()
#                     )
#                 )
#                 new_id = (await db.fetch_one(
#                     select(task_docs_table.c.task_doc_id).where(task_docs_table.c.project_task_id == payload.project_task_id)
#                 ))["task_doc_id"]
#             else:
#                 new_version = doc_version + 1
#                 logger.info(f"Document exists with version {new_version} for Task ID: {payload.project_task_id}, inserting new row with version 1.0")
#                 await db.execute(
#                     update(task_docs_table)
#                     .where(task_docs_table.c.project_task_id == payload.project_task_id)
#                     .values(is_latest=False)
#                 )
#                 new_doc = {
#                     "project_task_id": payload.project_task_id,
#                     "project_phase_id": phase_id,
#                     "project_id": project_id,
#                     "document_json": payload.document_json,
#                     "doc_version": new_version,
#                     "created_by": payload.updated_by,
#                     "submitted_by": payload.updated_by,
#                     "created_date": datetime.utcnow(),
#                     "is_latest": True
#                 }
#                 new_id = await db.execute(task_docs_table.insert().values(new_doc))
#
#         # Mark user as submitted
#         logger.debug(
#             f"Database session type: {type(db)}, executing update for User ID: {payload.updated_by}, Task ID: {payload.project_task_id}")
#         update_stmt = (
#             update(project_task_users_table)
#             .where(
#                 and_(
#                     project_task_users_table.c.project_task_id == payload.project_task_id,
#                     project_task_users_table.c.user_id == payload.updated_by
#                 )
#             )
#             .values(submitted=True)
#         )
#         logger.debug(f"Executing SQL: {str(update_stmt)}")
#         try:
#             result = await db.execute(update_stmt)
#             logger.debug(f"Execute result: {result}")
#             if result == 1:
#                 logger.info(
#                     f"Successfully marked user as submitted - User ID: {payload.updated_by} for Task ID: {payload.project_task_id}")
#             else:
#                 logger.error(
#                     f"Failed to update project_task_users - No matching record for User ID: {payload.updated_by}, "
#                     f"Task ID: {payload.project_task_id}, Rows affected: {result}"
#                 )
#                 return JSONResponse(
#                     status_code=status.HTTP_404_NOT_FOUND,
#                     content={
#                         "status_code": status.HTTP_404_NOT_FOUND,
#                         "message": "User-task mapping not found",
#                         "data": None
#                     }
#                 )
#         except Exception as e:
#             logger.error(
#                 f"Database operation failed - Error updating project_task_users for "
#                 f"User ID: {payload.updated_by}, Task ID: {payload.project_task_id}: {str(e)}"
#             )
#             return JSONResponse(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 content={
#                     "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                     "message": f"Database operation failed: {str(e)}",
#                     "data": None
#                 }
#             )
#
#         # Update task submission count
#         await db.execute(
#             update(project_tasks_list_table)
#             .where(project_tasks_list_table.c.project_task_id == payload.project_task_id)
#             .values(
#                 task_users_submitted=task_users_submitted,
#                 updated_by=payload.updated_by,
#                 updated_date=datetime.utcnow()
#             )
#         )
#         logger.info(f"Updated project tasks - Submission Count: {task_users_submitted} for Task ID: {payload.project_task_id}")
#
#         # Check if all users have submitted
#         if task_users_submitted < task_users_count:
#             logger.info(
#                 f"Not all users submitted - Submitted: {task_users_submitted} of {task_users_count} for Task ID: {payload.project_task_id}"
#             )
#             return {
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Submission saved. Waiting for other users",
#                 "data": {"task_doc_id": new_id, "doc_version": 1.0}
#             }
#
#         # All users submitted, finalize task
#         await db.execute(
#             update(project_tasks_list_table)
#             .where(project_tasks_list_table.c.project_task_id == payload.project_task_id)
#             .values(
#                 task_status_id=payload.task_status_id,
#                 updated_by=payload.updated_by,
#                 updated_date=datetime.utcnow()
#             )
#         )
#         logger.info(f"Finalized current task - Status set to: {payload.task_status_id} for Task ID: {payload.project_task_id}")
#
#         # Activate next task
#         query_next_task = select(project_tasks_list_table.c.project_task_id).where(
#             and_(
#                 project_tasks_list_table.c.project_phase_id == phase_id,
#                 project_tasks_list_table.c.task_status_id == 8,  # Assuming 8 = Pending
#                 project_tasks_list_table.c.project_task_id > payload.project_task_id
#             )
#         ).order_by(project_tasks_list_table.c.project_task_id.asc()).limit(1)
#         next_task = await db.fetch_one(query_next_task)
#         if next_task:
#             next_task_id = next_task["project_task_id"]
#             await db.execute(
#                 update(project_tasks_list_table)
#                 .where(project_tasks_list_table.c.project_task_id == next_task_id)
#                 .values(
#                     task_status_id=1,  # Active
#                     updated_by=payload.updated_by,
#                     updated_date=datetime.utcnow()
#                 )
#             )
#             logger.info(f"Activated next task - Task ID: {next_task_id} set to Active (status_id = 1)")
#         else:
#             logger.info(f"No next task found for Phase ID: {phase_id}")
#
#         # Check if all tasks in phase are completed
#         query_tasks_completed = select(func.count()).select_from(project_tasks_list_table).where(
#             and_(
#                 project_tasks_list_table.c.project_phase_id == phase_id,
#                 project_tasks_list_table.c.task_status_id != 3  # Assuming 3 = Completed
#             )
#         )
#         pending_tasks = await db.fetch_val(query_tasks_completed)
#         if pending_tasks == 0:
#             logger.info(f"All tasks completed for Phase ID: {phase_id}, closing phase")
#             await db.execute(
#                 update(project_phases_list_table)
#                 .where(project_phases_list_table.c.project_phase_id == phase_id)
#                 .values(
#                     status_id=7,  # Closed
#                     updated_by=payload.updated_by,
#                     updated_date=datetime.utcnow()
#                 )
#             )
#
#             # Activate next phase
#             query_next_phase = select(project_phases_list_table.c.project_phase_id).where(
#                 and_(
#                     project_phases_list_table.c.project_id == project_id,
#                     project_phases_list_table.c.status_id == 8,  # Pending
#                     project_phases_list_table.c.project_phase_id > phase_id
#                 )
#             ).order_by(project_phases_list_table.c.project_phase_id.asc()).limit(1)
#             next_phase = await db.fetch_one(query_next_phase)
#             if next_phase:
#                 next_phase_id = next_phase["project_phase_id"]
#                 await db.execute(
#                     update(project_phases_list_table)
#                     .where(project_phases_list_table.c.project_phase_id == next_phase_id)
#                     .values(
#                         status_id=1,  # Active
#                         updated_by=payload.updated_by,
#                         updated_date=datetime.utcnow()
#                     )
#                 )
#                 logger.info(f"Activated next phase - Phase ID: {next_phase_id}")
#
#                 # Activate first task in next phase
#                 query_first_task = select(project_tasks_list_table.c.project_task_id).where(
#                     and_(
#                         project_tasks_list_table.c.project_phase_id == next_phase_id,
#                         project_tasks_list_table.c.task_status_id == 8
#                     )
#                 ).order_by(project_tasks_list_table.c.project_task_id.asc()).limit(1)
#                 first_task = await db.fetch_one(query_first_task)
#                 if first_task:
#                     first_task_id = first_task["project_task_id"]
#                     await db.execute(
#                         update(project_tasks_list_table)
#                         .where(project_tasks_list_table.c.project_task_id == first_task_id)
#                         .values(
#                             task_status_id=1,
#                             updated_by=payload.updated_by,
#                             updated_date=datetime.utcnow()
#                         )
#                     )
#                     logger.info(f"Activated first task in next phase - Task ID: {first_task_id}")
#                 else:
#                     logger.info(f"No tasks found in next phase - Phase ID: {next_phase_id}")
#             else:
#                 # No next phase, mark project as completed
#                 await db.execute(
#                     update(projects)
#                     .where(projects.c.project_id == project_id)
#                     .values(
#                         status_id=3,  # Completed
#                         updated_by=payload.updated_by,
#                         updated_date=datetime.utcnow()
#                     )
#                 )
#                 logger.info(f"No next phase found for Project ID: {project_id}, marked project as completed")
#         else:
#             logger.info(f"Not all tasks completed for Phase ID: {phase_id}")
#
#         return {
#             "status_code": status.HTTP_200_OK,
#             "message": "Task fully submitted and status updated",
#             "data": {"task_doc_id": new_id, "doc_version": 1.0}
#         }
#
#     except Exception as e:
#         logger.error(f"Error in submit_project_task_document_service: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": "Internal Server Error",
#                 "data": None
#             }
#         )

import logging
import json
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_


logger = logging.getLogger(__name__)

async def submit_project_task_document_service(db, payload):
    try:
        logger.info(f"Starting submit_project_task_document_service for Task ID: {payload.project_task_id}, User ID: {payload.updated_by}")
        # Validate required parameters
        if not all([payload.project_task_id, payload.document_json, payload.task_status_id, payload.updated_by]):
            logger.warning("Missing required fields: project_task_id, document_json, task_status_id, or updated_by")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "All parameters are required",
                    "data": None
                }
            )

        # Call PostgreSQL function
        query = """
            SELECT ai_verify_transaction.submit_project_task_document_v2(
                :project_task_id,
                :document_json,
                :task_status_id,
                :updated_by
            ) AS result
        """
        params = {
            "project_task_id": payload.project_task_id,
            "document_json": payload.document_json,
            "task_status_id": payload.task_status_id,
            "updated_by": payload.updated_by
        }
        logger.debug(f"Executing SQL: {query} with params: {params}")
        result = await db.fetch_one(query, values=params)
        logger.debug(f"Function result: {result}")

        if not result or not result["result"]:
            logger.error(f"PostgreSQL function returned no result for Task ID: {payload.project_task_id}, User ID: {payload.updated_by}")
            return JSONResponse(
                content={
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Database function failed to return a result",
                    "data": None
                }
            )

        # Parse JSON string and return as JSONResponse
        parsed_result = json.loads(result["result"])
        return JSONResponse(
            content=parsed_result
        )

    except Exception as e:
        logger.error(f"Error in submit_project_task_document_service: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal Server Error: {str(e)}",
                "data": None
            }
        )
        
        
# async def get_phase_documents_by_project_task_id(db, project_task_id: int):
#     try:
#         logger.info(f"Fetching phase documents for project_task_id={project_task_id}")

#         # 1. Validate input
#         if not project_task_id:
#             logger.warning("Project Task ID is missing in request.")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": status.HTTP_400_BAD_REQUEST,
#                     "message": "project_task_id is required",
#                     "data": {}
#                 }
#             )
        
#         phase_query = select(project_tasks_list_table.c.project_phase_id).where(
#                     project_tasks_list_table.c.project_task_id == project_task_id)                   
#         phase_row = await db.fetch_one(phase_query)
        
#         if not phase_row:
#             return []
#         project_phase_id = phase_row.project_phase_id

#         phase_task_ids_subq = (
#             select(project_tasks_list_table.c.project_task_id)
#             .where(project_tasks_list_table.c.project_phase_id == project_phase_id)
#         )

#         task_doc_rows = await db.fetch_all(
#             select(
#                 task_docs_table.c.task_doc_id,
#                 task_docs_table.c.project_task_id,
#                 task_docs_table.c.project_phase_id,
#                 task_docs_table.c.doc_version,
#                 sdlc_tasks_table.c.task_name,
#                 sdlc_phases_table.c.phase_code
#             )
#             .join(project_tasks_list_table, task_docs_table.c.project_task_id == project_tasks_list_table.c.project_task_id)
#             .join(sdlc_tasks_table, project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id)
#             .join(project_phases_list_table, task_docs_table.c.project_phase_id == project_phases_list_table.c.project_phase_id)
#             .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
#             .where(
#                 and_(
#                     task_docs_table.c.project_task_id.in(phase_task_ids_subq),
#                     task_docs_table.c.doc_version != None
#                 )
#             )
#         )

#         # 1️⃣1️⃣ Build phase-doc lookup with format: phase_task_version
#         phase_docs_dict = {}
#         for row in task_doc_rows:
#             phase_docs_dict.setdefault(row.project_phase_id, []).append({
#                 "task_doc_id": row.task_doc_id,
#                 "project_task_id": row.project_task_id,
#                 "phase_name_doc_version": f"{row.phase_code}_{row.task_name}_{row.doc_version}"
#             })


#         # 5. Return response
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status_code": status.HTTP_200_OK,
#                 "message": "Phase documents fetched successfully.",
#                 "data": phase_docs_dict
#             }
#         )

#     except Exception as e:
#         logger.exception(f"Error while fetching phase documents for task_id={project_task_id}: {str(e)}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 "message": "Internal server error",
#                 "data": {}
#             }
#         )
        
        
        
        
        
from sqlalchemy import select, and_

async def get_phase_documents_by_project_task_id(db, project_task_id: int):
    """
    Given a project_task_id, fetch all task documents for all tasks
    in the same project phase.
    """
    # Step 1: Find the phase of the given task
    phase_query = select(project_tasks_list_table.c.project_phase_id).where(
        project_tasks_list_table.c.project_task_id == project_task_id
    )
    phase_row = await db.fetch_one(phase_query)

    if not phase_row:
        return []  # No such task found

    project_phase_id = phase_row.project_phase_id

    # Step 2: Subquery – all task IDs under that phase
    phase_task_ids_subq = (
        select(project_tasks_list_table.c.project_task_id)
        .where(project_tasks_list_table.c.project_phase_id == project_phase_id)
    )

    # Step 3: Fetch documents for all those tasks
    task_doc_rows = await db.fetch_all(
        select(
            task_docs_table.c.task_doc_id,
            task_docs_table.c.project_task_id,
            task_docs_table.c.doc_version,
            sdlc_tasks_table.c.task_name,
            sdlc_phases_table.c.phase_code,
        )
        .join(
            project_tasks_list_table,
            task_docs_table.c.project_task_id == project_tasks_list_table.c.project_task_id,
        )
        .join(
            sdlc_tasks_table,
            project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id,
        )
        .join(
            project_phases_list_table,
            project_tasks_list_table.c.project_phase_id == project_phases_list_table.c.project_phase_id,
        )
        .join(
            sdlc_phases_table,
            project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id,
        )
        .where(
            and_(
                task_docs_table.c.project_task_id.in_(phase_task_ids_subq),
                task_docs_table.c.doc_version.isnot(None),
            )
        )
    )

    docs_list = [dict(row) for row in task_doc_rows]
    safe_data = jsonable_encoder(docs_list)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status_code": status.HTTP_200_OK,
            "message": "Phase document fetched Successfully",
            "data": safe_data
        }
    )
