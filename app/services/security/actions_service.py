from fastapi import Request
from sqlalchemy import select, insert, update,desc
from app.db.database import database
from app.db.master.actions import actions_table
from datetime import datetime


# ------------------------------
# Get all active actions
# ------------------------------
async def get_all_actions_service(request: Request):
    try:
        query = (
            select(actions_table)
            .where(actions_table.c.is_active == True)
            .order_by(desc(actions_table.c.updated_date))  # 👈 latest first
        )
        rows = await database.fetch_all(query)

        result = [
            {
                "ActionId": r["action_id"],
                "ActionName": r["action_name"]
            }
            for r in rows
        ]

        return {
            "status_code": 200,
            "message": "Fetched active actions successfully",
            "data": result,
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {err}",
            "data": None,
        }


# ------------------------------
# Add a new action
# ------------------------------
async def add_action_service(request: Request, user_id: int):
    try:
        body = await request.json()
        action_name = body.get("ActionName")

        query = (
            insert(actions_table)
            .values(action_name=action_name, is_active=True, created_by=user_id)
            .returning(actions_table.c.action_id)
        )
        new_id = await database.execute(query)

        return {
            "status_code": 201,
            "message": "Action added successfully",
            "data": {"ActionId": new_id, "ActionName": action_name},
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {err}",
            "data": None,
        }


# ------------------------------
# Update an action
# ------------------------------
async def update_action_service(request: Request, action_id: int, updated_by: int):
    try:
        body = await request.json()
        action_name = body.get("ActionName")

        query = (
            update(actions_table)
            .where(actions_table.c.action_id == action_id, actions_table.c.is_active == True)
            .values(action_name=action_name, updated_by=updated_by, updated_date=datetime.utcnow())
            .returning(actions_table.c.action_id)
        )
        updated_id = await database.execute(query)

        if not updated_id:
            return {
                "status_code": 404,
                "message": "Action not found",
                "data": None,
            }

        return {
            "status_code": 200,
            "message": "Action updated successfully",
            "data": {"ActionId": action_id, "ActionName": action_name},
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {err}",
            "data": None,
        }


# ------------------------------
# Soft delete an action
# ------------------------------
async def delete_action_service(request: Request, action_id: int):
    try:
        query = (
            update(actions_table)
            .where(actions_table.c.action_id == action_id, actions_table.c.is_active == True)
            .values(is_active=False)
            .returning(actions_table.c.action_id)
        )
        deleted_id = await database.execute(query)

        if not deleted_id:
            return {
                "status_code": 404,
                "message": "Action not found",
                "data": None,
            }

        return {
            "status_code": 200,
            "message": "Action deleted successfully",
            "data": {"ActionId": action_id},
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {err}",
            "data": None,
        }
