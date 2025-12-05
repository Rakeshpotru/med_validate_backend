import os
import logging
from http.client import HTTPException
from sqlalchemy import select, insert, func, and_, desc, case, Integer, update
from typing import List, Optional
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.exc import SQLAlchemyError
from app.db import risk_sdlcphase_mapping_table, task_docs_table, project_comments_table, incident_report_table, \
    testing_asset_types_table, change_request_user_mapping_table
from app.db import equipment_list_table, status_table
from app.db.database import database
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.transaction.project_files import project_files_table
from app.db.master import status
from app.db.transaction.change_request import change_request_table
from app.schemas.transaction.project_schema import ProjectDetailResponse, UserInfo, PhaseInfo, TaskInfo, ProjectOut, \
    UserData, ProjectDetailUserResponse, ProjectDetailPhaseResponse, ProjectDetailsResponse, ProjectDetailTaskResponse, \
    ProjectDetailFileResponse, ProjectDetailTaskDocResponse, UpdateProjectDetailsRequest
from datetime import datetime,timezone
from app.db.transaction.projects import projects
from app.db.transaction.users import users
from app.db.transaction.projects_user_mapping import projects_user_mapping_table
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.transaction.project_phase_users import project_phase_users_table
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.project_task_users import project_task_users_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.user_roles import user_roles_table
from app.db.master.risk_assessment import risk_assessment_table
from app.db.master.sdlc_tasks import sdlc_tasks_table
from fastapi import status, UploadFile
import asyncio
from sqlalchemy.sql import true
from collections import defaultdict
from sqlalchemy import text
import json
from typing import Dict, Any
from fastapi.encoders import jsonable_encoder
from datetime import datetime
from fastapi import Request
from app.db.transaction.json_template_transactions import json_template_transactions
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()
CR_APPROVER_ROLES = os.getenv("CR_APPROVER_ROLES")
CR_APPROVER_ROLES = [int(r.strip()) for r in CR_APPROVER_ROLES.split(",")]

async def get_project_detail(project_id: int) -> Optional[ProjectDetailResponse]:
    try:
        # 1️⃣ Fetch project + core info
        project_query = (
            select(
                projects.c.project_id,
                projects.c.project_name,
                projects.c.project_description,
                projects.c.created_date,
                projects.c.status_id,
                risk_assessment_table.c.risk_assessment_id,
                risk_assessment_table.c.risk_assessment_name,
            )
            .join(
                risk_assessment_table,
                projects.c.risk_assessment_id == risk_assessment_table.c.risk_assessment_id
            )
            .where(
                and_(
                    projects.c.project_id == project_id,
                    projects.c.is_active == True,
                    risk_assessment_table.c.is_active == True
                )
            )
        )
        proj = await database.fetch_one(project_query)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        # 2️⃣ Fetch project users (active only)
        user_query = (
            select(
                users.c.user_id,
                users.c.user_name,
                user_roles_table.c.role_id,
                user_roles_table.c.role_name
            )
            .select_from(
                projects_user_mapping_table
                .join(users, projects_user_mapping_table.c.user_id == users.c.user_id)
                .outerjoin(user_role_mapping_table, user_role_mapping_table.c.user_id == users.c.user_id)
                .outerjoin(user_roles_table, user_role_mapping_table.c.role_id == user_roles_table.c.role_id)
            )
            .where(
                and_(
                    projects_user_mapping_table.c.project_id == project_id,
                    projects_user_mapping_table.c.is_active == True,
                    users.c.is_active == True
                )
            )
        )
        user_rows = await database.fetch_all(user_query)
        usersdata = [UserInfo(**row._mapping) for row in user_rows]

        # 3️⃣ Fetch all phases
        phase_rows = await database.fetch_all(
            select(
                project_phases_list_table.c.project_phase_id,
                project_phases_list_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                sdlc_phases_table.c.order_id
            )
            .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
            .where(
                and_(
                    project_phases_list_table.c.project_id == project_id,
                    sdlc_phases_table.c.is_active == True
                )
            )
            .order_by(sdlc_phases_table.c.order_id)
        )
        phase_ids = [p.project_phase_id for p in phase_rows]

        # 4️⃣ Fetch tasks for all phases
        task_rows = await database.fetch_all(
            select(
                project_tasks_list_table.c.project_task_id,
                project_tasks_list_table.c.project_phase_id,
                project_tasks_list_table.c.task_status_id.label("status_id"),
                sdlc_tasks_table.c.task_name,
                sdlc_tasks_table.c.order_id
            )
            .join(sdlc_tasks_table, project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id)
            .where(project_tasks_list_table.c.project_phase_id.in_(phase_ids))
            .order_by(sdlc_tasks_table.c.order_id)
        )
        task_ids = [t.project_task_id for t in task_rows]

        # 5️⃣ Fetch phase users
        phase_user_rows = await database.fetch_all(
            select(
                project_phase_users_table.c.project_phase_id,
                users.c.user_id,
                users.c.user_name
            )
            .join(users, project_phase_users_table.c.user_id == users.c.user_id)
            .where(
                and_(
                    project_phase_users_table.c.project_phase_id.in_(phase_ids),
                    project_phase_users_table.c.user_is_active == True,
                    users.c.is_active == True
                )
            )
        )

        # 6️⃣ Fetch task users
        if task_ids:
            task_user_rows = await database.fetch_all(
                select(
                    project_task_users_table.c.project_task_id,
                    users.c.user_id,
                    users.c.user_name
                )
                .join(users, project_task_users_table.c.user_id == users.c.user_id)
                .where(
                    and_(
                        project_task_users_table.c.project_task_id.in_(task_ids),
                        project_task_users_table.c.user_is_active == True,
                        users.c.is_active == True
                    )
                )
            )
        else:
            task_user_rows = []

        # 7️⃣ Build lookup dictionaries
        phase_users_dict = {}
        for row in phase_user_rows:
            phase_users_dict.setdefault(row.project_phase_id, []).append(
                UserData(user_id=row.user_id, user_name=row.user_name)
            )

        task_users_dict = {}
        for row in task_user_rows:
            task_users_dict.setdefault(row.project_task_id, []).append(
                UserData(user_id=row.user_id, user_name=row.user_name)
            )

        tasks_by_phase = {}
        for t in task_rows:
            tasks_by_phase.setdefault(t.project_phase_id, []).append(
                TaskInfo(
                    task_id=t.project_task_id,
                    task_name=t.task_name,
                    status_id=t.status_id,
                    task_users=task_users_dict.get(t.project_task_id, [])
                )
            )

        # 8️⃣ Build phases
        phases: List[PhaseInfo] = []
        for p in phase_rows:
            phase_tasks = tasks_by_phase.get(p.project_phase_id, [])
            phase_status = max([t.status_id for t in phase_tasks], default=1)
            phases.append(
                PhaseInfo(
                    phase_id=p.project_phase_id,
                    phase_name=p.phase_name,
                    status_id=phase_status,
                    phase_users=phase_users_dict.get(p.project_phase_id, []),
                    tasks=phase_tasks
                )
            )

        # 9️⃣ Fetch project files
        file_query = select(project_files_table.c.file_name).where(project_files_table.c.project_id == project_id)
        file_rows = await database.fetch_all(file_query)
        file_names = [row.file_name for row in file_rows]

        # 🔟 Fetch task docs where doc_version is not null, include phase + task names
        task_doc_rows = await database.fetch_all(
            select(
                task_docs_table.c.task_doc_id,
                task_docs_table.c.project_task_id,
                task_docs_table.c.project_phase_id,
                task_docs_table.c.doc_version,
                sdlc_tasks_table.c.task_name,
                sdlc_phases_table.c.phase_name
            )
            .join(project_tasks_list_table, task_docs_table.c.project_task_id == project_tasks_list_table.c.project_task_id)
            .join(sdlc_tasks_table, project_tasks_list_table.c.task_id == sdlc_tasks_table.c.task_id)
            .join(project_phases_list_table, task_docs_table.c.project_phase_id == project_phases_list_table.c.project_phase_id)
            .join(sdlc_phases_table, project_phases_list_table.c.phase_id == sdlc_phases_table.c.phase_id)
            .where(
                and_(
                    task_docs_table.c.project_id == project_id,
                    task_docs_table.c.doc_version != None
                )
            )
        )

        # 1️⃣1️⃣ Build phase-doc lookup with format: phase_task_version
        phase_docs_dict = {}
        for row in task_doc_rows:
            phase_docs_dict.setdefault(row.project_phase_id, []).append({
                "task_doc_id": row.task_doc_id,
                "phase_name_doc_version": f"{row.phase_name}_{row.task_name}_{row.doc_version}"
            })

        # Attach docs to phases
        for phase in phases:
            phase.task_docs = phase_docs_dict.get(phase.phase_id, [])

        # 🔁 Return final response
        return ProjectDetailResponse(
            project_id=proj.project_id,
            project_name=proj.project_name,
            description=proj.project_description,
            risk_assessment_id=proj.risk_assessment_id,
            risk_assessment_name=proj.risk_assessment_name,
            created_date=proj.created_date,
            status_id=proj.status_id,
            users=usersdata,
            phases=phases,
            project_files=file_names
        )

    except Exception as e:
        logger.exception(f"Error fetching project details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

UPLOAD_FOLDER = "project_files"
CR_UPLOAD_FOLDER = "change_request_files"
now = datetime.now()
async def create_project_service(payload, files=None, change_request_file=None, request=None):
    try:
        created_by = request.state.user["user_id"]
        logger.info("Start to create project.")

        # 1. Validation: project_name required
        if not payload.project_name or payload.project_name.strip() == "":
            logger.warning("Project name is missing.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Project name is required",
                    "data": None
                }
            )

        # 2. Validation: at least one user
        if not payload.user_ids or len(payload.user_ids) == 0:
            logger.warning("No user IDs provided.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "At least one user_id is required",
                    "data": None
                }
            )

        # 3. Validation: at least one phase
        if not payload.phase_ids or len(payload.phase_ids) == 0:
            logger.warning("No phase IDs provided.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "At least one phase_id is required",
                    "data": None
                }
            )

        # Validation for change_request_code
        if change_request_file and (not payload.change_request_code or payload.change_request_code.strip() == ""):
            logger.warning("Change request number is missing.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Change request number is required",
                    "data": None
                }
            )
        # Validation for change_request_file (required)
        if (not change_request_file) and (not payload.change_request_json):
            logger.warning("Change request file and json is missing.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "CR form or file is required",
                    "data": None
                }
            )
        # 4. Duplicate check: project_name case-insensitive & active
        duplicate_query = (
            select(projects.c.project_id)
            .where(func.lower(projects.c.project_name) == payload.project_name.lower())
            .where(projects.c.is_active == True)
        )
        existing_project = await database.fetch_one(duplicate_query)
        if existing_project:
            logger.warning("Project '%s' already exists.", payload.project_name)
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"Project '{payload.project_name}' already exists",
                    "data": None
                }
            )

        # Handle change_request_code generation for change_request_json
        if payload.change_request_json:
            # Generate change_request_code if not provided
            current_year = now.year
            change_request_code = payload.change_request_code

            # Find the latest change_request_code for the current year
            query = select(change_request_table.c.change_request_code) \
                .where(change_request_table.c.change_request_code.like(f"CR-{current_year}-%")) \
                .order_by(change_request_table.c.change_request_id.desc()) \
                .limit(1)
            latest_code_row = await database.fetch_one(query)

            if latest_code_row:
                # Extract the numeric part from the latest change_request_code (e.g., '45' from 'CR-2025-45')
                latest_code = latest_code_row["change_request_code"]
                parts = latest_code.split('-')
                latest_number = int(parts[-1]) if parts[-1].isdigit() else 0
                new_number = latest_number + 1
                change_request_code = f"CR-{current_year}-{new_number}"
            else:
                # If no records, generate the first change_request_code for the current year
                change_request_code = f"CR-{current_year}-1"

            # Set the generated change_request_code to the payload
            payload.change_request_code = change_request_code

        if payload.start_date and payload.end_date:
            if payload.end_date < payload.start_date:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status_code": 400, "message": "End date cannot be earlier than start date", "data": None}
                )

        async with database.transaction():
            # 4. Insert project
            insert_project = insert(projects).values(
                project_name=payload.project_name,
                project_description=payload.project_description,
                risk_assessment_id=payload.risk_assessment_id,
                equipment_id=payload.equipment_id,
                created_by=created_by,
                created_date=now,
                start_date=payload.start_date,  # <-- include start_date
                end_date=payload.end_date,  # <-- include end_date
                # status_id=1,
                status_id=8,
                # Added fields
                renewal_year=payload.renewal_year,
                make=payload.make,
                model=payload.model,
                json_template_id=payload.json_template_id,
                is_active=True
            )
            project_id = await database.execute(insert_project)

            # 5. Insert user mappings
            for user_id in payload.user_ids:
                await database.execute(
                    insert(projects_user_mapping_table).values(
                        project_id=project_id,
                        user_id=user_id,
                        is_active=True
                    )
                )

            # 6. Get phases for risk_assessment
            phase_query = (
                select(sdlc_phases_table.c.phase_id)
                .where(sdlc_phases_table.c.phase_id.in_(payload.phase_ids))
                .where(sdlc_phases_table.c.is_active == True)
                .order_by(sdlc_phases_table.c.order_id)
            )
            ordered_phase_rows = await database.fetch_all(phase_query)

            # 9. Insert phases and tasks
            for p_index, phase_row in enumerate(ordered_phase_rows):
                phase_id = phase_row.phase_id
                phase_order = p_index + 1
                # status_id = 1 if phase_order == 1 else 8
                insert_phase = insert(project_phases_list_table).values(
                    project_id=project_id,
                    phase_id=phase_id,
                    phase_order_id=phase_order,
                    status_id = 8
                )
                project_phase_id = await database.execute(insert_phase)

                task_query = (
                    select(sdlc_phase_tasks_mapping_table.c.task_id)
                    .where(sdlc_phase_tasks_mapping_table.c.phase_id == phase_id)
                    .where(sdlc_phase_tasks_mapping_table.c.is_active == True)
                )
                task_rows = await database.fetch_all(task_query)

                for t_index, task_row in enumerate(task_rows):
                    # status_id = 1 if (p_index == 0 and t_index == 0) else 8
                    await database.execute(
                        insert(project_tasks_list_table).values(
                            project_phase_id=project_phase_id,
                            task_id=task_row.task_id,
                            task_order_id=t_index + 1,
                            task_status_id=8
                        )
                    )

            # 8. Handle file uploads
            if files:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                for file in files:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    extension = os.path.splitext(file.filename)[1]
                    filename = f"{timestamp}_{file.filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)

                    content = await file.read()
                    with open(file_path, "wb") as f:
                        f.write(content)

                    await database.execute(
                        insert(project_files_table).values(
                            project_id=project_id,
                            file_name=filename,
                            is_active=True  # Always send True when creating a project file
                        )
                    )

            # CHANGE REQUEST: FILE OR JSON HANDLING
            transaction_template_id = None
            cr_filename = None
            # Case A: FILE upload
            if change_request_file:
                os.makedirs(CR_UPLOAD_FOLDER, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                extension = os.path.splitext(change_request_file.filename)[1]
                cr_filename = f"{timestamp}_{change_request_file.filename}"
                cr_file_path = os.path.join(CR_UPLOAD_FOLDER, cr_filename)
                cr_content = await change_request_file.read()
                with open(cr_file_path, "wb") as f:
                    f.write(cr_content)

            # Case B: JSON upload
            elif payload.change_request_json:
                insert_json = (
                    insert(json_template_transactions)
                    .values(
                        template_json=payload.change_request_json,
                        created_by=created_by,
                        created_date=datetime.now(),
                    )
                    .returning(json_template_transactions.c.transaction_template_id)
                )
                transaction_template_id = await database.execute(insert_json)
            # Insert into change_request table
            change_request_id = await database.execute(
                insert(change_request_table).values(
                    change_request_code=payload.change_request_code,
                    change_request_file=cr_filename,
                    project_id=project_id,
                    transaction_template_id=transaction_template_id,
                    is_verified=None,
                )
            )

            # Now insert into change_request_user_mapping_table for role 1, 3, or 6 users
            for user_id in payload.user_ids:
                # Get the role of the user from user_role_mapping_table
                role_query = (
                    select(user_role_mapping_table.c.role_id)
                    .where(user_role_mapping_table.c.user_id == user_id)
                )
                user_role = await database.fetch_one(role_query)
                if user_role and user_role['role_id'] in CR_APPROVER_ROLES:
                    # Insert into change_request_user_mapping_table
                    await database.execute(
                        insert(change_request_user_mapping_table).values(
                            change_request_id=change_request_id,
                            verified_by=user_id,
                            verified_date=None,
                            is_verified=None,
                            reject_reason=None,
                            user_is_active=True
                        )
                    )
            #
            logger.info("Project created successfully with ID %s", project_id)
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "status_code": status.HTTP_201_CREATED,
                    "message": "Project created successfully",
                    "data": {
                        "project_id": project_id,
                        "project_name": payload.project_name
                    }
                }
            )

    except Exception as e:
        logger.error("Project creation failed: %s", str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": None
            }
        )

async def get_all_projects_by_user_id(user_id: int):
    query = (
        select(
            projects.c.project_id,
            projects.c.project_name,
            projects.c.project_description,  # fixed column name
            projects.c.created_date,
            status_table.c.status_id,
            status_table.c.status_name,
            risk_assessment_table.c.risk_assessment_id,
            risk_assessment_table.c.risk_assessment_name,
            equipment_list_table.c.equipment_id,
            equipment_list_table.c.equipment_name,
        )
        .select_from(
            projects
            .join(status_table, projects.c.status_id == status_table.c.status_id)
            .join(risk_assessment_table, projects.c.risk_assessment_id == risk_assessment_table.c.risk_assessment_id)
            .join(equipment_list_table, projects.c.equipment_id == equipment_list_table.c.equipment_id)
            .join(projects_user_mapping_table, projects.c.project_id == projects_user_mapping_table.c.project_id)
        )
        .where(
            and_(
                projects_user_mapping_table.c.user_id == user_id,
                projects_user_mapping_table.c.is_active == True,  # ✅ filter mapping
                 projects.c.is_active == True,                    # ✅ filter projects
                # status_table.c.is_active == True,                # optional
                # risk_assessment_table.c.is_active == True,       # optional
                # equipment_list_table.c.is_active == True         # optional
            )
        )
        .order_by(desc(projects.c.created_date))
    )
    return await database.fetch_all(query)





async def get_all_projects():
    try:
        logger.info("Start fetching all active projects.")
        query = (
            select(
                projects.c.project_id,
                projects.c.project_name,
                projects.c.project_description,
                projects.c.created_date,
                status_table.c.status_id,
                status_table.c.status_name,
                risk_assessment_table.c.risk_assessment_id,
                risk_assessment_table.c.risk_assessment_name,
                equipment_list_table.c.equipment_id,
                equipment_list_table.c.equipment_name,
            )
            .select_from(
                projects
                .join(status_table, projects.c.status_id == status_table.c.status_id)
                .join(risk_assessment_table, projects.c.risk_assessment_id == risk_assessment_table.c.risk_assessment_id)
                .join(equipment_list_table, projects.c.equipment_id == equipment_list_table.c.equipment_id)
            )
            .where(projects.c.is_active == True)
            .order_by(projects.c.project_id.desc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active projects found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No projects found",
                    "data": []
                }
            )

        # Convert rows to Pydantic models and handle datetime
        result = []
        for row in rows:
            row_dict = dict(row)
            if isinstance(row_dict.get("created_date"), datetime):
                row_dict["created_date"] = row_dict["created_date"].isoformat()
            result.append(ProjectOut(**row_dict))

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Projects fetched successfully",
                "data": [r.dict() for r in result]
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching projects: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )



async def new_get_all_projects(user_id: int):
    try:
        query = "SELECT ai_verify_transaction.get_all_projects(:user_id) AS data"
        row = await database.fetch_one(query, values={"user_id": user_id})

        data = row["data"]  # this may be a string
        if isinstance(data, str):
            data = json.loads(data)  # parse string into Python list

        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "message": "Projects fetched successfully",
                "data": data  # now it's a proper list
            }
        )

    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status_code": 500, "message": "Internal server error", "data": []}
        )




async def get_project_details_service(project_id: int):
    try:
        logger.info("Fetching project details for ID %s", project_id)

        # 1. Fetch project details with joins for names
        project_query = (
            select(
                projects.c.project_id,
                projects.c.project_name,
                projects.c.project_description,
                projects.c.risk_assessment_id,
                risk_assessment_table.c.risk_assessment_name.label("risk_assessment_name"),
                projects.c.equipment_id,
                equipment_list_table.c.equipment_name.label("equipment_name"),
                equipment_list_table.c.asset_type_id.label("asset_type_id"),
                testing_asset_types_table.c.asset_name.label("asset_type_name"),
                projects.c.created_by,
                users.c.user_name.label("created_by_name"),
                projects.c.created_date,
                projects.c.start_date,
                projects.c.end_date,
                projects.c.status_id,
                projects.c.is_active,
                projects.c.renewal_year,
                projects.c.make,
                projects.c.model,
                projects.c.json_template_id,

            )
            .select_from(projects)
            .join(
                risk_assessment_table,
                risk_assessment_table.c.risk_assessment_id == projects.c.risk_assessment_id,
            )
            .outerjoin(
                equipment_list_table,
                equipment_list_table.c.equipment_id == projects.c.equipment_id,
            )
            .outerjoin(
                testing_asset_types_table,
                testing_asset_types_table.c.asset_id == equipment_list_table.c.asset_type_id,
            )
            .join(users, users.c.user_id == projects.c.created_by)
            .where(and_(projects.c.project_id == project_id, projects.c.is_active.is_(True)))
        )
        project_row = await database.fetch_one(project_query)
        if not project_row:
            logger.warning("Project with ID %s not found.", project_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project not found",
                    "data": None,
                },
            )

        project_data = dict(project_row)

        # Convert datetimes
        for field in ("created_date", "start_date", "end_date"):
            value = project_data.get(field)
            if value:
                project_data[field] = value.isoformat()

        # 2. Fetch associated users
        users_query = (
            select(
                projects_user_mapping_table.c.user_id,
                users.c.user_name.label("user_name"),
            )
            .join(users, users.c.user_id == projects_user_mapping_table.c.user_id)
            .where(
                and_(
                    projects_user_mapping_table.c.project_id == project_id,
                    projects_user_mapping_table.c.is_active.is_(True),
                )
            )
        )
        user_rows = await database.fetch_all(users_query)
        users_list = [dict(row) for row in user_rows]

        # 3. Fetch project files
        files_query = (
            select(
                project_files_table.c.project_file_id.label("file_id"),
                project_files_table.c.file_name,
            )
            .where(
                and_(
                    project_files_table.c.project_id == project_id,
                    project_files_table.c.is_active.is_(True),
                )
            )
        )

        file_rows = await database.fetch_all(files_query)
        files_list = [dict(row) for row in file_rows]

        # 4. ✅ Fetch project phases (ordered)
        phases_query = (
            select(
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                sdlc_phases_table.c.phase_code,
                project_phases_list_table.c.phase_order_id.label("order_id"),
            )
            .join(
                sdlc_phases_table,
                sdlc_phases_table.c.phase_id == project_phases_list_table.c.phase_id,
            )
            .where(project_phases_list_table.c.project_id == project_id)
            .order_by(project_phases_list_table.c.phase_order_id.asc())
        )
        phase_rows = await database.fetch_all(phases_query)
        phases_list = [dict(row) for row in phase_rows]

        # 5.Fetch change request details
        change_request_query = (
            select(
                change_request_table.c.change_request_id,
                change_request_table.c.change_request_code,
                change_request_table.c.change_request_file,
                change_request_table.c.is_verified,
                change_request_table.c.transaction_template_id,
                json_template_transactions.c.template_json,
            )
            .select_from(change_request_table)
            .outerjoin(
                json_template_transactions,
                json_template_transactions.c.transaction_template_id == change_request_table.c.transaction_template_id,
            )
            .where(change_request_table.c.project_id == project_id)
            .order_by(change_request_table.c.change_request_id.desc())
            .limit(1)
        )

        change_request_row = await database.fetch_one(change_request_query)

        if change_request_row:

            cr_id = change_request_row["change_request_id"]
            cr_is_verified = change_request_row["is_verified"]

            # -----------------------------------------
            # NEW RULE: If main table is_verified IS NOT FALSE
            # Return NULL reject reason directly
            # -----------------------------------------
            if cr_is_verified is not False:
                project_data["change_request_id"] = cr_id
                project_data["change_request_code"] = change_request_row["change_request_code"]
                project_data["change_request_file"] = change_request_row["change_request_file"]
                project_data["is_verified"] = cr_is_verified
                project_data["reject_reason"] = []
                project_data["transaction_template_id"] = change_request_row["transaction_template_id"]
                project_data["change_request_json"] = change_request_row["template_json"]
            else:
                # --------------------------------------------------------
                # NEW LOGIC: Fetch rejection reasons from user-mapping
                # Only if is_verified == False
                # --------------------------------------------------------
                reject_query = (
                    select(
                        users.c.user_name,
                        change_request_user_mapping_table.c.reject_reason,
                    )
                    .select_from(change_request_user_mapping_table)
                    .join(users, users.c.user_id == change_request_user_mapping_table.c.verified_by)
                    .where(
                        and_(
                            change_request_user_mapping_table.c.change_request_id == cr_id,
                            change_request_user_mapping_table.c.is_verified.is_(False),
                            change_request_user_mapping_table.c.user_is_active.is_(True)
                        )
                    )
                )

                reject_rows = await database.fetch_all(reject_query)
                reject_list = [dict(row) for row in reject_rows]

                project_data["change_request_id"] = cr_id
                project_data["change_request_code"] = change_request_row["change_request_code"]
                project_data["change_request_file"] = change_request_row["change_request_file"]
                project_data["is_verified"] = cr_is_verified

                # If user-level rejection exists use those
                if reject_list:
                    project_data["reject_reason"] = reject_list
                else:
                    project_data["reject_reason"] = []

                project_data["transaction_template_id"] = change_request_row["transaction_template_id"]
                project_data["change_request_json"] = change_request_row["template_json"]

        else:
            project_data["change_request_id"] = None
            project_data["change_request_code"] = None
            project_data["change_request_file"] = None
            project_data["is_verified"] = None
            project_data["reject_reason"] = []
            project_data["transaction_template_id"] = None
            project_data["change_request_json"] = None

        # 5. Combine all into response
        response_data = {
            **project_data,
            "users": users_list,
            "files": files_list,
            "phases": phases_list,  # ✅ added
        }

        logger.info(f"Project details fetched successfully for ID {project_id}")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Project details fetched successfully",
                "data": response_data,
            },
        )

    except SQLAlchemyError as e:
        logger.exception(f"Database error while fetching project {project_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Database error occurred",
                "data": None,
            },
        )
    except Exception as e:
        logger.exception(f"Error fetching project {project_id}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": None,
            },
        )

# Update_project_service
async def update_project_details_service(
    request: Request,
    project_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    renewal_year: Optional[str] = None,
    make: Optional[str] = None,
    model: Optional[str] = None,
    files: Optional[List[UploadFile]] = None,
    remove_file_ids: Optional[List[int]] = None,
    add_user_ids: Optional[List[int]] = None,
    remove_user_ids: Optional[List[int]] = None,
    change_request_code: Optional[str] = None,
    change_request_file: Optional[UploadFile] = None,
    change_request_json: Optional[str] = None,
    change_request_id: Optional[int] = None,
):
    try:
        updated_by = request.state.user["user_id"]
        # Step 1: Fetch project details
        project_query = (
            select(projects.c.project_id, projects.c.status_id, projects.c.start_date)
            .where(projects.c.project_id == project_id)
            .where(projects.c.is_active == True)
        )
        project_row = await database.fetch_one(project_query)
        if not project_row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": status.HTTP_404_NOT_FOUND, "message": "Project not found.", "data": None},
            )

        project_status = project_row.status_id
        existing_start_date = project_row.start_date
        # Step 1.5: Check for duplicate project name if title is provided
        if title is not None:
            duplicate_query = (
                select(projects.c.project_id)
                .where(projects.c.project_name == title)
                .where(projects.c.project_id != project_id)
                .where(projects.c.is_active == True)
            )
            duplicate_row = await database.fetch_one(duplicate_query)
            if duplicate_row:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"Project '{title}' already exists.",
                        "data": None,
                    },
                )
        # Step 2: Prepare update dictionary
        update_dict = {}
        if title is not None:
            update_dict["project_name"] = title
        if description is not None:
            update_dict["project_description"] = description
        if renewal_year is not None:
            try:
                update_dict["renewal_year"] = int(renewal_year) if renewal_year != "" else None
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "Invalid renewal_year format. Must be an integer.", "data": None},
                )
        if make is not None:
            update_dict["make"] = make if make != "" else None
        if model is not None:
            try:
                update_dict["model"] = int(model) if model != "" else None
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "Invalid model format. Must be an integer.", "data": None},
                )

        update_dict["updated_date"] = datetime.now()
        update_dict["updated_by"] = updated_by

        # Handle start_date logic
        if start_date is not None:
            try:
                parsed_start = datetime.fromisoformat(start_date)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "Invalid start_date format.", "data": None},
                )

            if existing_start_date is None:
                update_dict["start_date"] = parsed_start
                update_dict["status_id"] = 8  # First start_date sets status=8
            else:
                if parsed_start != existing_start_date:
                    update_dict["start_date"] = parsed_start
                # No error returned; modification is now allowed

        # Handle end_date
        if end_date is not None:
            if end_date == "":
                update_dict["end_date"] = None
            else:
                try:
                    parsed_end = datetime.fromisoformat(end_date)
                    update_dict["end_date"] = parsed_end
                except ValueError:
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "Invalid end_date format.", "data": None},
                    )

        # Update project info
        if update_dict:
            await database.execute(
                projects.update().where(projects.c.project_id == project_id).values(**update_dict)
            )

        # Step 3: Handle file operations
        if remove_file_ids:
            for fid in remove_file_ids:
                await database.execute(
                    project_files_table.update()
                    .where(project_files_table.c.project_file_id == fid)
                    .where(project_files_table.c.project_id == project_id)
                    .values(is_active=False)
                )

        if files:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            for file in files:
                if file.filename:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    filename = f"{timestamp}_{file.filename}"
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    content = await file.read()
                    with open(file_path, "wb") as f:
                        f.write(content)
                    await database.execute(
                        insert(project_files_table).values(
                            project_id=project_id,
                            file_name=filename,
                            is_active=True,
                        )
                    )

        # Step 4: Handle user operations based on status
        if add_user_ids or remove_user_ids:
            # Add users
            if add_user_ids:
                for user_id in add_user_ids:
                    existing = await database.fetch_one(
                        select(projects_user_mapping_table)
                        .where(projects_user_mapping_table.c.project_id == project_id)
                        .where(projects_user_mapping_table.c.user_id == user_id)
                    )
                    if not existing:
                        # Insert new if no row exists
                        await database.execute(
                            insert(projects_user_mapping_table).values(
                                project_id=project_id,
                                user_id=user_id,
                                is_active=True,
                            )
                        )
                    elif not existing.is_active:
                        # Update to active if row exists but is inactive
                        await database.execute(
                            update(projects_user_mapping_table)
                            .where(projects_user_mapping_table.c.project_id == project_id)
                            .where(projects_user_mapping_table.c.user_id == user_id)
                            .values(is_active=True)
                        )

            # Remove users only when status = 8
            if remove_user_ids:
                if project_status != 8:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "status_code": status.HTTP_403_FORBIDDEN,
                            "message": "Cannot remove users unless project status is 8.",
                            "data": None,
                        },
                    )
                for user_id in remove_user_ids:
                    existing = await database.fetch_one(
                        select(projects_user_mapping_table)
                        .where(projects_user_mapping_table.c.project_id == project_id)
                        .where(projects_user_mapping_table.c.user_id == user_id)
                    )
                    if existing:
                        await database.execute(
                            update(projects_user_mapping_table)
                            .where(projects_user_mapping_table.c.project_id == project_id)
                            .where(projects_user_mapping_table.c.user_id == user_id)
                            .values(is_active=False)
                        )
                    # If no existing row, do nothing (idempotent)

        # Step 5: Fetch updated project info
        updated_project_query = (
            select(
                projects.c.project_name.label("title"),
                projects.c.project_description.label("description"),
                projects.c.start_date,
                projects.c.end_date,
                projects.c.renewal_year,
                projects.c.make,
                projects.c.model,
            )
            .where(projects.c.project_id == project_id)
            .where(projects.c.is_active == True)
        )
        project_row = await database.fetch_one(updated_project_query)
        project_data = dict(project_row._mapping)
        project_data["start_date"] = project_data["start_date"].isoformat() if project_data["start_date"] else None
        project_data["end_date"] = project_data["end_date"].isoformat() if project_data["end_date"] else None

        # Files
        files_query = (
            select(
                project_files_table.c.project_file_id.label("file_id"),
                project_files_table.c.file_name,
                project_files_table.c.is_active,
            )
            .where(project_files_table.c.project_id == project_id)
        )
        file_rows = await database.fetch_all(files_query)
        files_list = [
            {
                "file_id": row.file_id,
                "file_name": row.file_name,
                "is_active": row.is_active,
            }
            for row in file_rows
        ]

        # Users
        users_query = (
            select(projects_user_mapping_table.c.user_id)
            .where(projects_user_mapping_table.c.project_id == project_id)
            .where(projects_user_mapping_table.c.is_active == True)
        )
        user_rows = await database.fetch_all(users_query)
        users_list = [row.user_id for row in user_rows]

        response_data = {**project_data, "files": files_list, "users": users_list}

        # Handle optional change request upload
        new_cr_id = None
        target_cr_id = change_request_id  # default: old CR

        if change_request_code and project_status == 8:
            old_cr_id = change_request_id

            # CASE A: New file uploaded
            if change_request_file and getattr(change_request_file, "filename", "").strip():
                os.makedirs(CR_UPLOAD_FOLDER, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                filename = f"{timestamp}_{change_request_file.filename}"
                file_path = os.path.join(CR_UPLOAD_FOLDER, filename)
                content = await change_request_file.read()
                with open(file_path, "wb") as f:
                    f.write(content)

                new_cr_id = await database.execute(
                    insert(change_request_table).values(
                        change_request_code=change_request_code,
                        change_request_file=filename,
                        project_id=project_id,
                        transaction_template_id=None,
                        is_verified=None,
                    ).returning(change_request_table.c.change_request_id)
                )

            # CASE B: New JSON submitted
            elif change_request_json and str(change_request_json).strip():
                try:
                    parsed_json = json.loads(change_request_json)
                except Exception:
                    parsed_json = change_request_json  # fallback to raw string if invalid

                # Correct way to get returned ID
                transaction_template_id = await database.execute(
                    insert(json_template_transactions).values(
                        template_json=parsed_json,
                        created_by=updated_by,
                        created_date=datetime.now()
                    ).returning(json_template_transactions.c.transaction_template_id)
                )

                new_cr_id = await database.execute(
                    insert(change_request_table).values(
                        change_request_code=change_request_code,
                        change_request_file=None,
                        project_id=project_id,
                        transaction_template_id=transaction_template_id,
                        is_verified=None,
                    ).returning(change_request_table.c.change_request_id)
                )

            # If a new CR was created → switch target and copy active approvers from old CR
            if new_cr_id:
                target_cr_id = new_cr_id

                if old_cr_id:
                    old_active_users = await database.fetch_all(
                        select(change_request_user_mapping_table.c.verified_by)
                        .where(
                            change_request_user_mapping_table.c.change_request_id == old_cr_id,
                            change_request_user_mapping_table.c.user_is_active == True
                        )
                    )
                    for row in old_active_users:
                        await database.execute(
                            insert(change_request_user_mapping_table).values(
                                change_request_id=target_cr_id,
                                verified_by=row.verified_by,
                                user_is_active=True,
                                is_verified=None,
                                reject_reason=None
                            )
                        )

            # === SAFE & INCREMENTAL APPROVER UPDATES (Your Exact Requirement) ===
            if target_cr_id:
                add_user_ids = add_user_ids or []
                remove_user_ids = remove_user_ids or []

                # Only modify approvers if at least one change is requested
                if add_user_ids or remove_user_ids:

                    # 1. Remove specified users
                    if remove_user_ids:
                        await database.execute(
                            update(change_request_user_mapping_table)
                            .where(
                                change_request_user_mapping_table.c.change_request_id == target_cr_id,
                                change_request_user_mapping_table.c.verified_by.in_(remove_user_ids)
                            )
                            .values(
                                user_is_active=False,
                                is_verified=None,
                                reject_reason=None
                            )
                        )

                    # 2. Add valid new approvers (only role 1 or 8)
                    if add_user_ids:
                        valid_adds = []
                        for uid in add_user_ids:
                            role_row = await database.fetch_one(
                                select(user_role_mapping_table.c.role_id)
                                .where(
                                    user_role_mapping_table.c.user_id == uid,
                                    user_role_mapping_table.c.is_active == True
                                )
                            )
                            if role_row and role_row.role_id in CR_APPROVER_ROLES:
                                valid_adds.append(uid)

                        for uid in valid_adds:
                            # Check if mapping already exists
                            existing = await database.fetch_one(
                                select(change_request_user_mapping_table.c.change_request_user_mapping_id)
                                .where(
                                    change_request_user_mapping_table.c.change_request_id == target_cr_id,
                                    change_request_user_mapping_table.c.verified_by == uid
                                )
                            )

                            if existing:
                                # Reactivate if exists but was inactive
                                await database.execute(
                                    update(change_request_user_mapping_table)
                                    .where(
                                        change_request_user_mapping_table.c.change_request_user_mapping_id == existing.change_request_user_mapping_id)
                                    .values(
                                        user_is_active=True,
                                        is_verified=None,
                                        reject_reason=None
                                    )
                                )
                            else:
                                # Insert new mapping
                                await database.execute(
                                    insert(change_request_user_mapping_table).values(
                                        change_request_id=target_cr_id,
                                        verified_by=uid,
                                        user_is_active=True,
                                        is_verified=None,
                                        reject_reason=None
                                    )
                                )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Project updated successfully.",
                "data": response_data,
            },
        )

    except Exception as e:
        logger.exception("Unexpected error in update_project_details_service")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": {"error": str(e)},
            },
        )


# delete_project_service
async def delete_project_service(project_id: int):
    try:
        logger.info("Attempting to archive project with ID %s", project_id)

        # Check if project exists & active
        project_check_query = select(projects).where(projects.c.project_id == project_id)
        existing_project = await database.fetch_one(project_check_query)

        if not existing_project:
            logger.warning("Project with ID %s not found.", project_id)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project not found",
                    "data": None,
                }
            )

        if not existing_project["is_active"]:
            logger.warning("Project with ID %s is already archived.", project_id)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Project is already archived",
                    "data": None,
                }
            )

        # ✅ Soft Delete (Archive)
        update_query = (
            projects.update()
            .where(projects.c.project_id == project_id)
            .values(
                is_active=False,
                updated_date=datetime.utcnow(),
            )
        )
        await database.execute(update_query)

        logger.info("Project ID %s successfully archived.", project_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Project archived successfully",
                "data": {"project_id": project_id},
            },
        )

    except SQLAlchemyError as e:
        logger.exception("Database error during archive for project %s: %s", project_id, e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Database error occurred",
                "data": None,
            },
        )

    except Exception as e:
        logger.exception("Unexpected error archiving project %s: %s", project_id, e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal server error: {str(e)}",
                "data": None,
            },
        )


# api to show dashboard data
async def get_dashboard_data(payload):
    try:
        query = """
            SELECT ai_verify_transaction.get_dashboard_data_v1(
                CAST(:p_user_id AS INTEGER),
                CAST(:p_project_id AS INTEGER)
            ) AS result;
        """

        params = {
            "p_user_id": payload.user_id,
            "p_project_id": payload.project_id,
        }


        rows = await database.fetch_all(query, values=params)

        if not rows or not rows[0]["result"]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": 404,
                    "message": "No dashboard data found.",
                    "data": {"projects": []},
                },
            )

        raw_result = rows[0]["result"]
        response_data = json.loads(raw_result) if isinstance(raw_result, str) else raw_result

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "Dashboard data fetched successfully.",
                "data": response_data,
            },
        )

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": 500,
                "message": f"An error occurred while fetching dashboard data: {str(e)}",
                "data": {"projects": []},
            },
        )    
    
    
