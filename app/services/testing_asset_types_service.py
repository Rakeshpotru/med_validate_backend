from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.db import testing_asset_types_table
from app.db.database import database
from app.schemas.testing_asset_types_schema import TestingAssetTypeResponse
import logging

logger = logging.getLogger(__name__)

async def get_all_testing_asset_types():
    try:
        logger.info("Fetching all active testing asset types...")
        query = (
            select(testing_asset_types_table)
            .where(testing_asset_types_table.c.is_active == True)
            .order_by(testing_asset_types_table.c.asset_id.desc())
        )
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active testing asset types found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No testing asset types found",
                    "data": []
                }
            )

        result = [TestingAssetTypeResponse(**row) for row in rows]

        logger.info("Testing asset types fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Testing asset types fetched successfully",
                "data": [r.dict() for r in result]
            }
        )

    except Exception as e:
        logger.error(f"Internal server error while fetching testing asset types: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )
