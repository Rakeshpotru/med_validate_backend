import logging
from fastapi import status
from fastapi.responses import JSONResponse
from app.db.database import database
from app.db.master.status import status_table
from app.schemas.status_schema import StatusResponse, StatusCreateRequest, StatusUpdateRequest, \
    StatusDeleteRequest
from sqlalchemy import select, and_, func

logger = logging.getLogger(__name__)

async def get_all_status():
    try:
        logger.info("Start to fetch all active status.")
        query = select(status_table).where(status_table.c.is_active == True).order_by(status_table.c.status_id.desc())
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active status found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No status found",
                    "data": []
                }
            )

        result = [StatusResponse(**row) for row in rows]

        logger.info("status fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "status fetched successfully",
                "data": [r.dict() for r in result]
            }
        )
    except Exception as e:

        logger.error(f"Internal server error while fetching status: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def create_status(payload: StatusCreateRequest):
    try:
        logger.info("Start to create status.")

        # 1. Validation: status name required
        if not payload.status_name or payload.status_name.strip() == "":
            logger.warning("status is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "status name is required",
                    "data": []
                }
            )

        # 2. Check if status exists (case-insensitive)
        query = select(status_table).where(
            func.lower(status_table.c.status_name) == payload.status_name.lower()
        )
        existing_status = await database.fetch_one(query)

        if existing_status:
            if existing_status.is_active:  # If already active
                logger.warning(f"status '{payload.status_name}' already exists.")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"Status '{payload.status_name}' already exists",
                        "data": []
                    }
                )
            else:
                # If inactive → Activate it
                update_query = (
                    status_table.update()
                    .where(status_table.c.status_id == existing_status.status_id)
                    .values(is_active=True)
                )
                await database.execute(update_query)

                logger.info(f"Inactive status '{payload.status_name}' activated with ID {existing_status.status_id}.")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": f"status '{payload.status_name}' activated successfully",
                        "data": {
                            "status_id": existing_status.status_id,
                            "status_name": payload.status_name
                        }
                    }
                )

        # 3. Insert new status if not found
        insert_query = status_table.insert().values(
            status_name=payload.status_name,
            is_active=payload.is_active
        )
        new_status_id = await database.execute(insert_query)

        logger.info(f"status '{payload.status_name}' created successfully with ID {new_status_id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Status created successfully",
                "data": {
                    "status_id": new_status_id,
                    "status_name": payload.status_name
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while creating status: {str(e)}")


        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def update_status(payload: StatusUpdateRequest):
    try:
        logger.info(f"Start to update status name for status ID: {payload.status_id}")

        # 1. Validation
        if not payload.status_id:
            logger.warning("status ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "status ID is required",
                    "data": []
                }
            )

        if not payload.status_name or payload.status_name.strip() == "":
            logger.warning("status name is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "status name is required",
                    "data": []
                }
            )

        # 2. Check if status exists by ID
        query = select(status_table).where(status_table.c.status_id == payload.status_id)
        existing_status = await database.fetch_one(query)

        if not existing_status:
            logger.warning(f"status ID {payload.status_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "status not found",
                    "data": []
                }
            )

        # 3. Check if new status name already exists for another status
        conflict_query = select(status_table).where(
            and_(
                func.lower(status_table.c.status_name) == payload.status_name.lower(),
                status_table.c.status_id != payload.status_id,
                status_table.c.is_active == True
            )
        )
        conflict_status = await database.fetch_one(conflict_query)

        if conflict_status:
            logger.warning(f"status name '{payload.status_name}' already exists for another status.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"status name '{payload.status_name}' already exists",
                    "data": []
                }
            )

        # 4. Update status name
        update_query = (
            status_table.update()
            .where(status_table.c.status_id == payload.status_id)
            .values(status_name=payload.status_name)
        )
        await database.execute(update_query)

        logger.info(f"status ID {payload.status_id} updated successfully to '{payload.status_name}'.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "status updated successfully",
                "data": {
                    "status_id": payload.status_id,
                    "status_name": payload.status_name
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while updating status: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

async def delete_status(payload: StatusDeleteRequest):
    try:
        logger.info(f"Start to delete (inactivate) status. status ID: {payload.status_id}")

        # 1. Validation
        if not payload.status_id:
            logger.warning("status ID is missing in request payload.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "status ID is required",
                    "data": []
                }
            )

        # 2. Check if status exists
        query = select(status_table).where(status_table.c.status_id == payload.status_id)
        existing_status = await database.fetch_one(query)

        if not existing_status:
            logger.warning(f"status ID {payload.status_id} not found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "status not found",
                    "data": []
                }
            )

        # 3. Check if already inactive
        if not existing_status.is_active:
            logger.warning(f"status ID {payload.status_id} is already inactive.")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": "status is already inactive",
                    "data": []
                }
            )

        # 4. Update status to inactive
        update_query = (
            status_table.update()
            .where(status_table.c.status_id == payload.status_id)
            .values(is_active=False)
        )
        await database.execute(update_query)

        logger.info(f"status ID {payload.status_id} marked as inactive successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "status inactivated successfully",
                "data": {
                    "status_id": payload.status_id,
                    "is_active": False
                }
            }
        )

    except Exception as e:
        logger.error(f"Internal error while inactivating status: {str(e)}")

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )
