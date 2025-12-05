import os
import logging
from fastapi import status, Request
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import select, join, or_

from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.database import database
from app.db.transaction.change_request import change_request_table
from app.db.transaction.projects import projects
from app.schemas.transaction.change_request_schema import ChangeRequestResponse, ChangeRequestVerifyUpdateRequest
from datetime import datetime, timezone
from app.db.transaction.projects_user_mapping import projects_user_mapping_table
from app.db.transaction.json_template_transactions import json_template_transactions
from app.db.transaction.change_request_user_mapping import change_request_user_mapping_table
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
UPLOAD_FOLDER = "change_request_files"
load_dotenv()
CR_APPROVER_ROLES = os.getenv("CR_APPROVER_ROLES")
CR_APPROVER_ROLES = [int(r.strip()) for r in CR_APPROVER_ROLES.split(",")]

async def get_unverified_change_requests(request: Request):
    try:
        login_user_id = request.state.user["user_id"]
        logger.info("Fetching unverified change requests for active projects.")
        # Join change_request and projects table
        j = (
            join(change_request_table, projects, change_request_table.c.project_id == projects.c.project_id)
            .join(projects_user_mapping_table, projects.c.project_id == projects_user_mapping_table.c.project_id)
            .join(
                json_template_transactions,
                change_request_table.c.transaction_template_id == json_template_transactions.c.transaction_template_id,
                isouter=True)
            .join(user_role_mapping_table,user_role_mapping_table.c.user_id == login_user_id,isouter=False)
            .join(change_request_user_mapping_table,
                  change_request_table.c.change_request_id == change_request_user_mapping_table.c.change_request_id,
                  isouter=True)
        )
        query = (
            select(
                change_request_table.c.change_request_id,
                change_request_table.c.change_request_code,
                change_request_table.c.change_request_file,
                change_request_user_mapping_table.c.reject_reason,
                projects.c.project_id,
                projects.c.project_name,
                change_request_user_mapping_table.c.is_verified,
                change_request_user_mapping_table.c.change_request_user_mapping_id,
                change_request_table.c.transaction_template_id,
                json_template_transactions.c.template_json.label("change_request_json"),
            )
            .select_from(j)
            .where(
                # change_request_table.c.is_verified == False,
                projects.c.is_active == True,
                projects_user_mapping_table.c.is_active == True,
                projects_user_mapping_table.c.user_id == login_user_id,
                user_role_mapping_table.c.role_id.in_(CR_APPROVER_ROLES),

                user_role_mapping_table.c.is_active == True,
                change_request_user_mapping_table.c.user_is_active == True,
                change_request_user_mapping_table.c.verified_by == login_user_id
            )
            .order_by(change_request_table.c.change_request_id.desc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No unverified change requests found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No unverified change requests found",
                    "data": []
                }
            )
        result = [
            {
                "change_request_id": row["change_request_id"],
                "change_request_code": row["change_request_code"],
                "change_request_file": row["change_request_file"],
                "reject_reason": row["reject_reason"],
                "transaction_template_id": row["transaction_template_id"],
                "change_request_json": row["change_request_json"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "is_verified": row["is_verified"],
                "change_request_user_mapping_id": row["change_request_user_mapping_id"],
            }
            for row in rows
        ]

        logger.info(f"Fetched {len(result)} unverified change requests successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Unverified change requests fetched successfully",
                "data": result
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching change requests: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def get_cr_file_service(file_name: str):
    try:
        logger.info(f"Fetching file: {file_name}")

        # Validate input
        if not file_name or file_name.strip() == "":
            logger.warning("Missing or empty file name.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "File name is required",
                    "data": None
                }
            )

        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        # Check if file exists
        if not os.path.isfile(file_path):
            logger.warning(f"File not found: {file_name}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "File not found",
                    "data": None
                }
            )

        # Return the file for download
        logger.info(f"Returning file: {file_name}")
        return FileResponse(
            path=file_path,
            filename=file_name,
            media_type="application/octet-stream",
            status_code=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error while returning file: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None
            }
        )


async def update_change_request_verification_status(payload: ChangeRequestVerifyUpdateRequest):
    try:
        logger.info(f"Updating verification status for Change Request ID: {payload.change_request_id}")

        # 1. Validate request payload
        if not payload.change_request_id or not payload.change_request_user_mapping_id:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "change_request_id and change_request_user_mapping_id are required",
                    "data": []
                }
            )

        # 2. Check if change request exists
        query = select(change_request_table).where(
            change_request_table.c.change_request_id == payload.change_request_id
        )
        existing_request = await database.fetch_one(query)

        if not existing_request:
            return JSONResponse(
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Change Request not found",
                    "data": []
                }
            )
        # 2.1 Handle change_request_json → create new template if provided
        new_template_id = None
        if payload.change_request_json not in (None, "", {}, []):
            try:
                insert_template = json_template_transactions.insert().values(
                    template_json=payload.change_request_json,
                    created_by=payload.verified_by,
                    created_date=datetime.utcnow()
                )
                result = await database.execute(insert_template)
                new_template_id = result

                # Update change_request_table with new transaction_template_id
                update_cr_template = (
                    change_request_table.update()
                    .where(change_request_table.c.change_request_id == payload.change_request_id)
                    .values(transaction_template_id=new_template_id)
                )
                await database.execute(update_cr_template)

                logger.info(
                    f"New JSON template created with ID: {new_template_id} for CR {payload.change_request_id}")
            except Exception as e:
                logger.error(f"Failed to save change_request_json: {str(e)}")

        # 3. Update the specific user-mapping row
        current_timestamp = datetime.utcnow()

        update_user_mapping = (
            change_request_user_mapping_table.update()
            .where(
                change_request_user_mapping_table.c.change_request_user_mapping_id
                == payload.change_request_user_mapping_id
            )
            .values(
                is_verified=payload.is_verified,
                verified_date=current_timestamp,
                reject_reason=payload.reject_reason
            )
        )
        await database.execute(update_user_mapping)

        # 4. Recalculate final verification for change_request
        fetch_mappings = select(
            change_request_user_mapping_table.c.is_verified
        ).where(
            (change_request_user_mapping_table.c.change_request_id == payload.change_request_id) &
            (change_request_user_mapping_table.c.user_is_active == True)
        )

        mappings = await database.fetch_all(fetch_mappings)

        statuses = [row["is_verified"] for row in mappings]

        if any(s is False for s in statuses):
            final_status = False
        elif all(s is True for s in statuses):
            final_status = True
        else:
            final_status = None

        update_change_request = (
            change_request_table.update()
            .where(change_request_table.c.change_request_id == payload.change_request_id)
            .values(is_verified=final_status)
        )
        await database.execute(update_change_request)
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Verification updated successfully",
                "data": {
                    "change_request_id": payload.change_request_id,
                    "final_status": final_status
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal server error: {str(e)}")
        return JSONResponse(
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )