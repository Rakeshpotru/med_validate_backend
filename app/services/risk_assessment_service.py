import logging
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_
from app.db.database import database
from app.db.master.risk_assessment import risk_assessment_table
from app.schemas.risk_assessment_schema import RiskAssessmentResponse, RiskAssessmentCreateRequest, \
    RiskAssessmentUpdateRequest, RiskAssessmentDeleteRequest

logger = logging.getLogger(__name__)

async def get_all_risk_assessments():
    try:
        logger.info("Start to fetch all active risk assessments.")
        query = select(risk_assessment_table).where(risk_assessment_table.c.is_active == True)
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active risk assessments found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No risk assessments found",
                    "data": []
                }
            )

        result = [RiskAssessmentResponse(**row) for row in rows]

        logger.info("Risk assessments fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Risk assessments fetched successfully",
                "data": [r.dict() for r in result]
            }
        )

    except Exception as e:
        logger.exception(f"Internal server error while fetching risk assessments: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )


# POST
async def create_risk_assessment(payload: RiskAssessmentCreateRequest):
    try:
        logger.info("Start to create risk assessment.")

        if not payload.risk_assessment_name or payload.risk_assessment_name.strip() == "":
            logger.warning("Risk assessment name is missing.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Risk assessment name is required",
                    "data": []
                }
            )

        # Check if already exists
        query = select(risk_assessment_table).where(
            func.lower(risk_assessment_table.c.risk_assessment_name) == payload.risk_assessment_name.lower()
        )
        existing = await database.fetch_one(query)

        if existing:
            if existing.is_active:
                logger.warning(f"Risk assessment '{payload.risk_assessment_name}' already exists.")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"Risk assessment '{payload.risk_assessment_name}' already exists",
                        "data": []
                    }
                )
            else:
                # Reactivate if inactive
                update_query = (
                    risk_assessment_table.update()
                    .where(risk_assessment_table.c.risk_assessment_id == existing.risk_assessment_id)
                    .values(is_active=True)
                )
                await database.execute(update_query)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": f"Risk assessment '{payload.risk_assessment_name}' reactivated successfully",
                        "data": {
                            "risk_assessment_id": existing.risk_assessment_id,
                            "risk_assessment_name": payload.risk_assessment_name
                        }
                    }
                )

        insert_query = risk_assessment_table.insert().values(
            risk_assessment_name=payload.risk_assessment_name,
            is_active=payload.is_active
        )
        new_id = await database.execute(insert_query)

        logger.info(f"Risk assessment '{payload.risk_assessment_name}' created with ID {new_id}")
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status_code": status.HTTP_201_CREATED,
                "message": "Risk assessment created successfully",
                "data": {
                    "risk_assessment_id": new_id,
                    "risk_assessment_name": payload.risk_assessment_name
                }
            }
        )
    except Exception as e:
        logger.error(f"Internal error while creating risk assessment: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )

# PUT
async def update_risk_assessment(payload: RiskAssessmentUpdateRequest):
    try:
        logger.info(f"Start to update risk assessment ID {payload.risk_assessment_id}")

        if not payload.risk_assessment_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "ID is required", "data": []}
            )

        if not payload.risk_assessment_name or payload.risk_assessment_name.strip() == "":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "Name is required", "data": []}
            )

        query = select(risk_assessment_table).where(
            risk_assessment_table.c.risk_assessment_id == payload.risk_assessment_id
        )
        existing = await database.fetch_one(query)

        if not existing:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": status.HTTP_404_NOT_FOUND, "message": "Not found", "data": []}
            )

        conflict_query = select(risk_assessment_table).where(
            and_(
                func.lower(risk_assessment_table.c.risk_assessment_name) == payload.risk_assessment_name.lower(),
                risk_assessment_table.c.risk_assessment_id != payload.risk_assessment_id,
                risk_assessment_table.c.is_active == True
            )
        )
        conflict = await database.fetch_one(conflict_query)
        if conflict:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "status_code": status.HTTP_409_CONFLICT,
                    "message": f"Name '{payload.risk_assessment_name}' already exists",
                    "data": []
                }
            )

        update_query = (
            risk_assessment_table.update()
            .where(risk_assessment_table.c.risk_assessment_id == payload.risk_assessment_id)
            .values(risk_assessment_name=payload.risk_assessment_name)
        )
        await database.execute(update_query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Updated successfully",
                "data": {
                    "risk_assessment_id": payload.risk_assessment_id,
                    "risk_assessment_name": payload.risk_assessment_name
                }
            }
        )
    except Exception as e:
        logger.error(f"Internal error while updating risk assessment: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": "Internal server error", "data": []}
        )

# DELETE
async def delete_risk_assessment(payload: RiskAssessmentDeleteRequest):
    try:
        logger.info(f"Start to delete (inactivate) risk assessment ID {payload.risk_assessment_id}")

        if not payload.risk_assessment_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status_code": status.HTTP_400_BAD_REQUEST, "message": "ID is required", "data": []}
            )

        query = select(risk_assessment_table).where(
            risk_assessment_table.c.risk_assessment_id == payload.risk_assessment_id
        )
        existing = await database.fetch_one(query)

        if not existing:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": status.HTTP_404_NOT_FOUND, "message": "Not found", "data": []}
            )

        if not existing.is_active:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"status_code": status.HTTP_409_CONFLICT, "message": "Already inactive", "data": []}
            )

        update_query = (
            risk_assessment_table.update()
            .where(risk_assessment_table.c.risk_assessment_id == payload.risk_assessment_id)
            .values(is_active=False)
        )
        await database.execute(update_query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Inactivated successfully",
                "data": {"risk_assessment_id": payload.risk_assessment_id, "is_active": False}
            }
        )
    except Exception as e:
        logger.error(f"Internal error while deleting risk assessment: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": status.HTTP_500_INTERNAL_SERVER_ERROR, "message": "Internal server error", "data": []}
        )