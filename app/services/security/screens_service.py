from sqlalchemy import select, insert, update,func
from app.db.database import database
from app.db.master.screens import screens_table

# ------------------------------
# Get all screens
# ------------------------------
async def get_all_screens_service():
    try:
        query = (select(screens_table)
                .where(screens_table.c.is_active == True))
        rows = await database.fetch_all(query)

        result = [
            {
                "ScreenId": r["screen_id"],
                "ScreenName": r["screen_name"],
                "IsActive": r["is_active"],
                "CreatedBy": r["created_by"],
                "CreatedDate": r["created_date"],
                "UpdatedBy": r["updated_by"],
                "UpdatedDate": r["updated_date"],
            }
            for r in rows
        ]

        if not result:
            return {"status_code": 404, "message": "No screens found", "data": []}

        return {"status_code": 200, "message": "Fetched all screens successfully", "data": result}

    except Exception as err:
        return {"status_code": 500, "message": f"Internal server error: {err}", "data": None}


# ------------------------------
# Add a new screen
# ------------------------------
async def add_screen_service(screen_name: str, user_id: int):
    try:
        query = (
            insert(screens_table)
            .values(screen_name=screen_name, created_by=user_id, is_active=True)
            .returning(screens_table.c.screen_id)
        )
        new_id = await database.execute(query)

        return {
            "status_code": 201,
            "message": "Screen added successfully",
            "data": {"ScreenId": new_id, "ScreenName": screen_name},
        }
    except Exception as err:
        return {"status_code": 500, "message": f"Internal server error: {err}", "data": None}


# ------------------------------
# Update a screen
# ------------------------------
async def update_screen_service(screen_id: int, screen_name: str, updated_by: int):
    try:
        update_query = (
            update(screens_table)
            .where(screens_table.c.screen_id == screen_id, screens_table.c.is_active == True)
            .values(screen_name=screen_name, updated_by=updated_by, updated_date=func.now())
            .returning(screens_table.c.screen_id)
        )
        updated_id = await database.execute(update_query)

        if not updated_id:
            return {"status_code": 404, "message": "Screen not found or inactive", "data": None}

        row = await database.fetch_one(select(screens_table).where(screens_table.c.screen_id == screen_id))

        screen_data = {
            "ScreenId": row["screen_id"],
            "ScreenName": row["screen_name"],
            "IsActive": row["is_active"],
            "CreatedBy": row["created_by"],
            "CreatedDate": row["created_date"],
            "UpdatedBy": row["updated_by"],
            "UpdatedDate": row["updated_date"],
        }

        return {"status_code": 200, "message": "Screen updated successfully", "data": screen_data}

    except Exception as err:
        return {"status_code": 500, "message": f"Internal server error: {err}", "data": None}


# ------------------------------
# Soft delete a screen
# ------------------------------
async def delete_screen_service(screen_id: int):
    try:
        delete_query = (
            update(screens_table)
            .where(screens_table.c.screen_id == screen_id, screens_table.c.is_active == True)
            .values(is_active=False)
            .returning(
                screens_table.c.screen_id,
                screens_table.c.screen_name,
                screens_table.c.is_active,
                screens_table.c.created_by,
                screens_table.c.created_date,
                screens_table.c.updated_by,
                screens_table.c.updated_date,
            )
        )
        deleted = await database.fetch_one(delete_query)

        if not deleted:
            return {"status_code": 404, "message": "Screen not found or already inactive", "data": None}

        return {
            "status_code": 200,
            "message": "Screen deleted successfully",
            "data": {
                "ScreenId": deleted["screen_id"],
                "ScreenName": deleted["screen_name"],
                "IsActive": deleted["is_active"],
                "CreatedBy": deleted["created_by"],
                "CreatedDate": deleted["created_date"],
                "UpdatedBy": deleted["updated_by"],
                "UpdatedDate": deleted["updated_date"],
            },
        }

    except Exception as err:
        return {"status_code": 500, "message": f"Internal server error: {err}", "data": None}
