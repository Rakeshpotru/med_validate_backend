# app/services/template_type_service.py
from fastapi import status, HTTPException,Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, join, func, insert
from app.db.database import database
from app.db.master.json_templates import json_templates_table
from app.db.master.template_format_types import template_format_types_table
from app.db.master.template_types import template_types_table
from app.schemas.template_type_schema import TemplateTypeFullResponse, CreateJsonTemplate, JsonTemplateResponse
import logging

logger = logging.getLogger(__name__)

async def get_all_template_types():
    try:
        logger.info("Fetching all active template types with their format details...")

        # Join template_types with template_format_types
        j = join(
            template_types_table,
            template_format_types_table,
            template_types_table.c.template_format_type_id == template_format_types_table.c.template_format_type_id
        )

        query = (
            select(
                template_types_table.c.template_type_id,
                template_types_table.c.template_type_name,
                template_types_table.c.is_active,
                template_types_table.c.template_format_type_id,
                template_format_types_table.c.format_name,
                template_format_types_table.c.section,
                template_format_types_table.c.weightage,
                template_format_types_table.c.table
            )
            .select_from(j)
            .where(template_types_table.c.is_active == True)
            # ✅ Order by ASCENDING (oldest first)
            .order_by(template_types_table.c.template_type_id.asc())
        )

        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active template types found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No active template types found",
                    "data": []
                }
            )

        result = [TemplateTypeFullResponse(**row) for row in rows]

        logger.info("Active template types fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Active template types fetched successfully",
                "data": [r.model_dump() for r in result]  # Updated for v2 consistency
            }
        )

    except Exception as e:
        logger.error(f"Error fetching template types: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def create_json_template(input: CreateJsonTemplate, request: Request):
    try:
        created_by = request.state.user["user_id"]
        logger.info(f"Creating new JSON template for template_type_id: {input.template_type_id}")

        # Check if template_type_id exists and is active (optional validation)
        type_query = select(template_types_table.c.template_type_id).where(
            template_types_table.c.template_type_id == input.template_type_id,
            template_types_table.c.is_active == True
        )
        existing_type = await database.fetch_one(type_query)
        if not existing_type:
            logger.warning(f"Invalid or inactive template_type_id: {input.template_type_id}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid or inactive template type",
                    "data": None
                }
            )

        # Fetch max version for the given template_type_id
        max_version_query = select(func.max(json_templates_table.c.template_version)).where(
            json_templates_table.c.template_type_id == input.template_type_id
        )
        max_version = await database.fetch_val(max_version_query)
        new_version = (max_version or 0) + 1

        # Insert new template with RETURNING to get the inserted ID and full row
        insert_query = insert(json_templates_table).values(
            template_name=input.template_name,
            template_type_id=input.template_type_id,
            json_template=input.json_template,
            created_by=created_by,
            template_version=new_version
        ).returning(json_templates_table)

        result = await database.fetch_one(insert_query)
        if not result:
            raise Exception("Failed to insert template")

        new_template_id = result.template_id
        response_data = JsonTemplateResponse(**dict(result))

        logger.info(f"New JSON template created with ID: {new_template_id}, version: {new_version}")

        serialized_data = response_data.model_dump(mode='json')  # ✅ Key fix: mode='json' serializes datetime to ISO str

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "JSON template created successfully",
                "data": serialized_data
            }
        )

    except Exception as e:
        logger.error(f"Error creating JSON template: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None
            }
        )

# New service: Get JSON template by ID
async def get_json_template_by_id(template_id: int):
    try:
        logger.info(f"Fetching JSON template with ID: {template_id}")

        query = select(json_templates_table).where(
            json_templates_table.c.template_id == template_id
        )
        row = await database.fetch_one(query)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="JSON template not found"
            )

        response_data = JsonTemplateResponse(**dict(row))
        serialized_data = response_data.model_dump(mode='json')

        logger.info(f"JSON template {template_id} fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "JSON template fetched successfully",
                "data": serialized_data
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching JSON template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# New service: Get all versions for a template_type_id
async def get_all_versions_by_type_id(template_type_id: int):
    try:
        logger.info(f"Fetching all versions for template_type_id: {template_type_id}")

        # Check if template_type_id exists and is active
        type_query = select(template_types_table.c.template_type_id).where(
            template_types_table.c.template_type_id == template_type_id,
            template_types_table.c.is_active == True
        )
        existing_type = await database.fetch_one(type_query)
        if not existing_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive template type"
            )

        # Fetch all versions ordered by version DESC (newest first)
        query = (
            select(json_templates_table)
            .where(json_templates_table.c.template_type_id == template_type_id)
            .order_by(json_templates_table.c.template_version.desc())
        )
        rows = await database.fetch_all(query)

        if not rows:
            logger.info(f"No versions found for template_type_id: {template_type_id}")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No versions found for this template type",
                    "data": []
                }
            )

        result = [JsonTemplateResponse(**dict(row)) for row in rows]
        serialized_data = [r.model_dump(mode='json') for r in result]

        logger.info(f"All versions for template_type_id {template_type_id} fetched successfully. Found {len(rows)} versions.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "All versions fetched successfully",
                "data": serialized_data  # Consistent with other endpoints: "data" is the list of versions
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching versions for template_type_id {template_type_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )