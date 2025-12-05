import os
import logging
from app.db.database import database
from app.db.master import status
from fastapi import status
import json
from typing import List, Dict, Any
from fastapi.responses import JSONResponse, FileResponse

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

UPLOAD_FOLDER = "project_files"

async def get_projects_by_user_service(db, user_id: int):
    try:
        logger.info(f"Fetching projects for user_id={user_id}")

        # Validate user_id
        if not user_id or user_id <= 0:
            logger.warning(f"Bad Request: Invalid user_id={user_id}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid user_id provided",
                    "data": None
                }
            )

        # Prepare query to call the PostgreSQL function
        query = """
            SELECT ai_verify_transaction.get_projects_by_user_for_myworks(:user_id) AS projects_json
        """
        params = {
            "user_id": user_id
        }

        logger.debug(f"Executing SQL: {query} with params: {params}")

        # Execute query
        result = await db.fetch_one(query, values=params)
        logger.debug(f"Function result: {result}")

        if not result or not result["projects_json"]:
            logger.error(f"No active projects found for user_id={user_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No active projects found for this user",
                    "data": None
                }
            )

        # Parse the JSON string from the function result
        try:
            projects_json_str = result["projects_json"].replace('""', '"')  # Fix escaped quotes
            projects_data = json.loads(projects_json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON for user_id={user_id}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"Error parsing JSON: {str(e)}",
                    "data": None
                }
            )

        # Return the parsed data in the proper format
        return JSONResponse(
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Projects fetched successfully",
                "data": projects_data  # Return the parsed projects data
            }
        )

    except Exception as e:
        logger.error(f"Error in get_projects_by_user_service for user_id={user_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Internal Server Error: {str(e)}",
                "data": None
            }
        )


async def get_project_details_by_id(project_id: int):
    try:
        if not project_id:
            logger.warning(f"Bad Request: Missing or invalid project_id.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Bad Request: Missing or invalid project_id",
                    "data": None,
                },
            )

        logger.info(f"Fetching project details for project_id: {project_id}")

        # Use plain SQL string instead of text() to avoid TextClause issues
        query = "SELECT ai_verify_transaction.get_project_details_v3(:project_id) AS response_json"
        row = await database.fetch_one(query, {"project_id": project_id})

        if row and row.response_json:
            response_data = json.loads(row.response_json)
            logger.info(
                f"Project details fetched successfully for project_id: {project_id} (Completed: {response_data['data']['completed_percentage']}%)"
            )
            return JSONResponse(content=response_data)
        else:
            # Fallback (should not occur if DB handles 404)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project not found",
                    "data": None,
                },
            )

    except Exception as e:
        logger.error(f"❌ Internal server error while fetching project details: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None,
            },
        )


async def get_user_tasks_service(db, user_id: int, project_id: int) -> Dict[str, Any]:

    # 1. Check if user_id is provided
    if not user_id:
        logger.error("User ID is required but not provided.")
        return {
            "status_code": 400,
            "message": "User ID is required.",
            "data": []
        }

    try:
        # Prepare the query to call the PostgreSQL function
        function_query = f"SELECT ai_verify_transaction.get_user_tasks_for_myworks4({user_id}, {project_id});"

        # 2. Fetch the result directly from the PostgreSQL function
        result = await db.fetch_all(function_query)

        # 3. Check for a valid response (200 condition)
        if result:
            # The function returns a single row with one column (a stringified JSON)
            raw_data = result[0][0]

            try:
                # First decode the outermost stringified JSON
                parsed_data = json.loads(raw_data)

                # Successful case: Return proper response with parsed data
                logger.info(f"Tasks fetched successfully for user_id {user_id}.")
                return {
                    "status_code": 200,
                    "message": "Tasks fetched successfully",
                    "data": parsed_data.get("data", [])  # Return the inner "data" list directly
                }

            except json.JSONDecodeError as e:
                # 4. Error in parsing JSON (500 condition)
                logger.error(f"Failed to parse JSON from database for user_id {user_id}: {str(e)}")
                return {
                    "status_code": 500,
                    "message": f"Failed to parse JSON from database: {str(e)}",
                    "data": []
                }
        else:
            # 5. No data found (404 or 400 condition)
            logger.warning(f"No tasks found for user_id {user_id} and project_id {project_id}.")
            return {
                "status_code": 404,
                "message": "No tasks found.",
                "data": []
            }

    except Exception as e:
        # 6. Generic error (500 condition)
        logger.error(f"An unexpected error occurred while fetching tasks for user_id {user_id}: {str(e)}")
        return {
            "status_code": 500,
            "message": f"An unexpected error occurred: {str(e)}",
            "data": []
        }


async def get_project_file_service(file_name: str):
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