import logging
from fastapi import status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,update,func,insert,and_
from app.db.database import database
from app.db.master.json_templates import json_templates_table
from app.db.master.template_types import template_types_table
from app.db.transaction.json_template_transactions import json_template_transactions
from datetime import datetime
# from app.db.master.risk_assessment_template import risk_assessment_template_table

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




async def get_latest_templates_by_type_service(template_type_id: int):
    """
    Service to fetch the latest JSON template for a given template_type_id.
    """
    try:
        if not template_type_id:
            return JSONResponse(
                status_code=400,
                content={"message": "Missing template_type_id"}
            )

        # Subquery: get latest version for this template_type_id
        subq = (
            select(
                json_templates_table.c.template_type_id,
                func.max(json_templates_table.c.template_version)
                .label("latest_version")
            )
            .where(
                json_templates_table.c.template_type_id == template_type_id
            )
            .group_by(json_templates_table.c.template_type_id)
        ).subquery()

        # Main query
        query = (
            select(
                json_templates_table.c.template_id,
                json_templates_table.c.template_name,
                json_templates_table.c.template_type_id,
                json_templates_table.c.json_template,
                json_templates_table.c.created_by,
                json_templates_table.c.created_date,
                json_templates_table.c.template_version,
                template_types_table.c.template_format_type_id
            )
            .select_from(
                json_templates_table
                .join(
                    template_types_table,
                    json_templates_table.c.template_type_id ==
                    template_types_table.c.template_type_id
                )
                .join(
                    subq,
                    and_(
                        json_templates_table.c.template_type_id ==
                        subq.c.template_type_id,
                        json_templates_table.c.template_version ==
                        subq.c.latest_version
                    )
                )
            )
            .limit(1)
        )

        row = await database.fetch_one(query)

        if not row:
            return JSONResponse(
                status_code=404,
                content={
                    "message": "No templates found for this template_type_id"
                }
            )

        data = dict(row)
        
        safe_data = jsonable_encoder(data)

        return JSONResponse(
            status_code=200,
            content={
                "message": f"Fetched latest template for template_type_id {template_type_id}",
                "data": safe_data
            }
        )

    except Exception as e:
        logger.error(f"Error fetching latest JSON template: {e}")
        return JSONResponse(
            status_code=500,
            content={"message": "Internal server error"}
        )


async def save_json_template_transaction_service(created_by: int, template_json: dict):
    """
    Service to insert a new JSON template transaction record.
    """
    try:
        if not created_by or not template_json:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Missing required parameters"},
            )

        query = insert(json_template_transactions).values(
            created_by=created_by,
            template_json=template_json,
            created_date=datetime.utcnow(),
        )
        # record_id = await database.execute(query)
        transaction_template_id = await database.execute(query)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Template saved successfully",
                "transaction_template_id": transaction_template_id,
            },
        )

    except Exception as e:
        logger.error(f"Error saving JSON template transaction: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )


async def get_json_template_by_id_service(transaction_template_id: int):
    """
    Fetch a saved JSON template transaction by its transaction_template_id.
    """
    try:
        if not transaction_template_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Missing transaction_template_id"},
            )

        query = select(json_template_transactions).where(
            json_template_transactions.c.transaction_template_id == transaction_template_id
        )
        row = await database.fetch_one(query)

        if not row:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": f"No template found for id {transaction_template_id}"},
            )

        safe_data = jsonable_encoder(dict(row))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Fetched JSON template successfully",
                "data": safe_data,
            },
        )

    except Exception as e:
        logger.error(f"Error fetching JSON template by ID: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )
