import logging
from datetime import datetime, timezone

from fastapi import status,Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, insert, update

from app.db import equipment_ai_docs_table, testing_asset_types_table
from app.db.database import database
from app.db.master.equipment import equipment_list_table

logger = logging.getLogger(__name__)



async def get_all_equipments():
    try:
        logger.info("Fetching all equipments...")

        query = (
            select(
                equipment_list_table.c.equipment_id.label("equipment_id"),
                equipment_list_table.c.equipment_name.label("equipment_name"),
                equipment_list_table.c.is_ai_verified.label("ai_verified_doc"),
                equipment_list_table.c.asset_type_id.label("asset_type_id"),

            )
            .where(equipment_list_table.c.is_active == True)
            .order_by(equipment_list_table.c.equipment_id.desc())
        )

        results = await database.fetch_all(query)

        if not results:
            return JSONResponse(
                status_code=404,
                content={
                    "status_code": 404,
                    "message": "No equipments found",
                    "data": []
                }
            )

        data = [dict(row) for row in results]

        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "message": "Equipments fetched successfully",
                "data": data
            }
        )

    except Exception as e:
        logger.exception(f"Error while fetching equipments: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "message": "Internal server error",
                "data": []
            }
        )

# ---------------- CREATE ----------------
async def create_equipment(name: str, asset_type_id: int, request: Request):
    created_by = request.state.user["user_id"]

    # Validate asset_type_id exists and is active
    asset_query = select(testing_asset_types_table).where(
        testing_asset_types_table.c.asset_id == asset_type_id,
        testing_asset_types_table.c.is_active == True
    )
    asset = await database.fetch_one(asset_query)

    if not asset:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "message": f"Invalid asset_type_id: {asset_type_id}",
                "data": []
            }
        )

    # Check for any equipment with the same name and asset_type_id (active or inactive)
    existing_query = select(equipment_list_table).where(
        equipment_list_table.c.equipment_name == name,
        equipment_list_table.c.asset_type_id == asset_type_id
    )
    existing = await database.fetch_one(existing_query)

    if existing:
        if existing["is_active"]:
            # Already active, cannot create duplicate
            return JSONResponse(
                status_code=409,
                content={
                    "status_code": 409,
                    "message": f"Equipment '{name}' already exists for asset type {asset_type_id}",
                    "data": []
                }
            )
        else:
            # Reactivate the inactive equipment
            query = (
                update(equipment_list_table)
                .where(equipment_list_table.c.equipment_id == existing["equipment_id"])
                .values(
                    is_active=True,
                    updated_by=created_by,
                    updated_date=datetime.now(timezone.utc)
                )
                .returning(equipment_list_table.c.equipment_id)
            )
            updated_row = await database.fetch_one(query)
            return JSONResponse(
                status_code=200,
                content={
                    "status_code": 200,
                    "message": "Equipment reactivated successfully",
                    "data": {
                        "equipment_id": updated_row["equipment_id"],
                        "equipment_name": name,
                        "asset_type_id": asset_type_id,
                        "updated_by": created_by
                    }
                }
            )
        

    # Insert new row if no existing equipment found
    query = (
        insert(equipment_list_table)
        .values(
            equipment_name=name,
            asset_type_id=asset_type_id,
            is_ai_verified=False,
            created_by=created_by,
            created_date=datetime.now(timezone.utc),
            is_active=True
        )
        .returning(equipment_list_table.c.equipment_id)
    )
    new_row = await database.fetch_one(query)
    return JSONResponse(
        status_code=201,
        content={
            "status_code": 201,
            "message": "Equipment created successfully",
            "data": {
                "equipment_id": new_row["equipment_id"],
                "equipment_name": name,
                "asset_type_id": asset_type_id,
                "created_by": created_by
            }
        }
    )


# ---------------- UPDATE ----------------
async def update_equipment(equipment_id: int, name: str, asset_type_id: int, request: Request):
    updated_by = request.state.user["user_id"]  # get from JWT

    try:
        existing_equipment = await database.fetch_one(
            select(equipment_list_table.c.is_active)
            .where(equipment_list_table.c.equipment_id == equipment_id)
        )

        if not existing_equipment:
            return JSONResponse(
                status_code=404,
                content={"status_code": 404, "message": "Equipment not found", "data": []}
            )

        if not existing_equipment["is_active"]:
            return JSONResponse(
                status_code=400,
                content={"status_code": 400, "message": "Equipment is inactive", "data": []}
            )

        query = (
            update(equipment_list_table)
            .where(equipment_list_table.c.equipment_id == equipment_id)
            .values(
                equipment_name=name,
                asset_type_id=asset_type_id,
                updated_by=updated_by,
                updated_date=datetime.now(timezone.utc)
            )
            .returning(equipment_list_table.c.equipment_id)
        )
        updated_row = await database.fetch_one(query)

        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "message": "Equipment updated successfully",
                "data": {
                    "equipment_id": updated_row["equipment_id"],
                    "equipment_name": name,
                    "asset_type_id": asset_type_id
                }
            }
        )

    except Exception as e:
        logger.exception(f"Error updating equipment: {e}")
        return JSONResponse(
            status_code=500,
            content={"status_code": 500, "message": "Internal server error", "data": []}
        )

# async def update_equipment(equipment_id: int, name: str, updated_by: int):
#     try:
#         # Check if equipment exists
#         existing_equipment = await database.fetch_one(
#             select(equipment_list_table.c.is_active)
#             .where(equipment_list_table.c.equipment_id == equipment_id)
#         )
#
#         if not existing_equipment:
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": 404,
#                     "message": "Equipment not found",
#                     "data": []
#                 }
#             )
#
#         # Check if equipment is inactive
#         if not existing_equipment["is_active"]:
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "status_code": 400,
#                     "message": "Equipment is inactive and cannot be updated",
#                     "data": []
#                 }
#             )
#
#         # Proceed to update equipment
#         logger.info(f"Updating equipment {equipment_id} -> {name}")
#         query = (
#             update(equipment_list_table)
#             .where(equipment_list_table.c.equipment_id == equipment_id)
#             .values(
#                 equipment_name=name,
#                 updated_by=updated_by,
#                 updated_date=datetime.now(timezone.utc)
#             )
#             .returning(equipment_list_table.c.equipment_id)
#         )
#
#         updated_row = await database.fetch_one(query)
#
#         if not updated_row:
#             # This case is unlikely now because we checked existence before
#             return JSONResponse(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 content={
#                     "status_code": 404,
#                     "message": "Equipment not found or could not be updated",
#                     "data": []
#                 }
#             )
#
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status_code": 200,
#                 "message": "Equipment updated successfully",
#                 "data": {
#                     "equipment_id": updated_row["equipment_id"],
#                     "equipment_name": name
#                 }
#             }
#         )
#
#     except Exception as e:
#         logger.exception(f"Error updating equipment: {e}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status_code": 500,
#                 "message": "Internal server error",
#                 "data": []
#             }
#         )


# ---------------- DELETE (SOFT) ----------------
async def delete_equipment(equipment_id: int, request: Request):
    updated_by = request.state.user["user_id"]  # get from JWT

    try:
        existing_equipment = await database.fetch_one(
            select(equipment_list_table.c.is_active)
            .where(equipment_list_table.c.equipment_id == equipment_id)
        )

        if not existing_equipment:
            return JSONResponse(
                status_code=404,
                content={"status_code": 404, "message": "Equipment not found", "data": []}
            )

        if not existing_equipment["is_active"]:
            return JSONResponse(
                status_code=400,
                content={"status_code": 400, "message": "Equipment is already inactive", "data": []}
            )

        query = (
            update(equipment_list_table)
            .where(equipment_list_table.c.equipment_id == equipment_id)
            .values(
                is_active=False,
                updated_by=updated_by,
                updated_date=datetime.now(timezone.utc)
            )
            .returning(equipment_list_table.c.equipment_id)
        )

        updated_row = await database.fetch_one(query)

        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "message": "Equipment deleted successfully",
                "data": {"equipment_id": updated_row["equipment_id"]}
            }
        )

    except Exception as e:
        logger.exception(f"Error deleting equipment: {e}")
        return JSONResponse(
            status_code=500,
            content={"status_code": 500, "message": "Internal server error", "data": []}
        )
