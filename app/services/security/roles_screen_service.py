import json
from collections import defaultdict

from fastapi import Request
from app.db.database import database
from app.schemas.security.roles_screen_schema import InsertRoleScreenActionsResponse, InsertRoleScreenActionsRequest, \
    InsertScreenActionMappingResponse, InsertScreenActionMappingRequest


# async def get_all_screens_service(request: Request):
#     """
#     Fetch all active screens
#     """
#     try:
#         query = """
#             SELECT json_agg(
#                 json_build_object(
#                     'ScreenId', s.screen_id,
#                     'ScreenName', s.screen_name,
#                     'IsActive', s.is_active,
#                     'CreatedBy', s.created_by,
#                     'CreatedDate', s.created_date
#                 )
#             ) AS result_json
#             FROM ai_verify_master.screens s
#             WHERE s.is_active = TRUE;
#         """
#
#         row = await database.fetch_one(query)
#
#         result = []
#         if row and row["result_json"]:
#             if isinstance(row["result_json"], str):
#                 result = json.loads(row["result_json"])
#             else:
#                 result = row["result_json"]
#
#         return {
#             "status_code": 200,
#             "message": "Fetched all screens successfully",
#             "data": result
#         }
#
#     except Exception as err:
#         return {
#             "status_code": 500,
#             "message": f"Internal server error: {str(err)}",
#             "data": None
#         }

# async def get_all_actions_service(request: Request):
#     """
#     Fetch all active actions (is_active = true)
#     """
#     try:
#         query = """
#             SELECT json_agg(
#                 json_build_object(
#                     'ActionId', a.action_id,
#                     'ActionName', a.action_name
#                 )
#             ) AS result_json
#             FROM ai_verify_master.actions a
#             WHERE a.is_active = TRUE;
#         """
#
#         row = await database.fetch_one(query)
#
#         result = []
#         if row and row["result_json"]:
#             if isinstance(row["result_json"], str):
#                 result = json.loads(row["result_json"])
#             else:
#                 result = row["result_json"]
#
#         return {
#             "status_code": 200,
#             "message": "Fetched active actions successfully",
#             "data": result
#         }
#
#     except Exception as err:
#         return {
#             "status_code": 500,
#             "message": f"Internal server error: {str(err)}",
#             "data": None
#         }


async def get_screen_action_mapping_service(request: Request):
    """
    Fetch all active screens with their mapped actions (optimized)
    """
    try:
        query = """
            SELECT 
                s.screen_id,
                s.screen_name,
                sam.screen_action_id,
                a.action_id,
                a.action_name
            FROM ai_verify_master.screens s
            JOIN ai_verify_security.screen_action_mapping sam 
                ON s.screen_id = sam.screen_id
            JOIN ai_verify_master.actions a
                ON sam.action_id = a.action_id
            WHERE s.is_active = TRUE
              AND sam.is_active = TRUE
              AND a.is_active = TRUE
            ORDER BY s.screen_id, a.action_id;
        """

        rows = await database.fetch_all(query)

        # Group screens → actions
        screens_dict = defaultdict(lambda: {"ScreenId": None, "ScreenName": None, "actions": []})

        for row in rows:
            screen_id = row["screen_id"]
            screens_dict[screen_id]["ScreenId"] = row["screen_id"]
            screens_dict[screen_id]["ScreenName"] = row["screen_name"]
            screens_dict[screen_id]["actions"].append({
                "ScreenActionId": row["screen_action_id"],
                "ActionId": row["action_id"],
                "ActionName": row["action_name"]
            })

        result = list(screens_dict.values())

        return {
            "status_code": 200,
            "message": "Fetched screen-action mappings successfully",
            "data": result
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {str(err)}",
            "data": None
        }



async def get_role_screen_actions_service(request: Request, role_id: int):
    try:
        query = """
            SELECT
                s.screen_id AS "ScreenId",
                s.screen_name AS "ScreenName",
                json_agg(
                    json_build_object(
                        'Screen_Action_ID', so.screen_action_id,
                        'ActionName', a.action_name,
                        'active', rsm.is_active
                    )
                ) AS actions
            FROM ai_verify_master.screens s
            JOIN ai_verify_security.screen_action_mapping so
              ON so.screen_id = s.screen_id
            JOIN ai_verify_master.actions a
              ON a.action_id = so.action_id
            JOIN ai_verify_security.screen_action_mapping_roles rsm
              ON rsm.screen_action_id = so.screen_action_id
             AND rsm.role_id = :role_id
             AND rsm.is_active = TRUE
            WHERE s.is_active = TRUE
              AND so.is_active = TRUE
              AND a.is_active = TRUE
            GROUP BY s.screen_id, s.screen_name
            ORDER BY s.screen_id;
        """

        rows = await database.fetch_all(query, values={"role_id": role_id})

        # If no rows, return empty list
        result = []
        for row in rows:
            if row["actions"] is not None:
                result.append({
                    "ScreenId": row["ScreenId"],
                    "ScreenName": row["ScreenName"],
                    "actions": row["actions"]
                })

        return {
            "status_code": 200,
            "message": "Fetched role screen actions successfully",
            "data": result
        }

    except Exception as err:
        return {
            "status_code": 500,
            "message": f"Internal server error: {str(err)}",
            "data": []
        }

async def insert_screen_action_mapping_service(
    request: Request,
    payload: InsertScreenActionMappingRequest
) -> InsertScreenActionMappingResponse:
    """
    Insert/Update/Deactivate screen → action mappings safely.
    Handles multiple action_ids per screen.
    """

    try:
        if not payload.items:
            return InsertScreenActionMappingResponse(
                status_code=400,
                message="No screen-action mappings provided",
                data=None
            )

        to_insert = []
        to_activate = []
        to_deactivate = []

        for item in payload.items:
            screen_id = item.screen_id

            # --- 1. Fetch existing mappings ---
            query = """
                SELECT * FROM ai_verify_security.screen_action_mapping
                WHERE screen_id = :screen_id
            """
            existing_records = await database.fetch_all(query, values={"screen_id": screen_id})
            existing_map = {rec["action_id"]: rec for rec in existing_records}
            incoming_ids = set(item.action_ids)

            # --- 2. Determine insert or activate ---
            for action_id in incoming_ids:
                if action_id not in existing_map:
                    # New mapping → insert
                    to_insert.append({
                        "screen_id": screen_id,
                        "action_id": action_id,
                        "is_active": item.is_active
                    })
                elif not existing_map[action_id]["is_active"]:
                    # Existing but inactive → activate
                    to_activate.append(existing_map[action_id]["screen_action_id"])

            # --- 3. Determine deactivate (soft delete) ---
            for action_id, rec in existing_map.items():
                if action_id not in incoming_ids and rec["is_active"]:
                    to_deactivate.append(rec["screen_action_id"])

        # --- 4. Execute DB operations ---

        # Insert new mappings or update existing ones
        if to_insert:
            insert_query = """
                INSERT INTO ai_verify_security.screen_action_mapping
                    (screen_id, action_id, is_active)
                VALUES (:screen_id, :action_id, :is_active)
                ON CONFLICT (screen_id, action_id) DO UPDATE
                SET is_active = EXCLUDED.is_active
            """
            await database.execute_many(insert_query, values=to_insert)

        # Activate previously inactive mappings
        if to_activate:
            activate_query = """
                UPDATE ai_verify_security.screen_action_mapping
                SET is_active = TRUE
                WHERE screen_action_id = ANY(:ids)
            """
            await database.execute(activate_query, values={"ids": to_activate})

        # Deactivate removed mappings
        if to_deactivate:
            deactivate_query = """
                UPDATE ai_verify_security.screen_action_mapping
                SET is_active = FALSE
                WHERE screen_action_id = ANY(:ids)
            """
            await database.execute(deactivate_query, values={"ids": to_deactivate})

        return InsertScreenActionMappingResponse(
            status_code=200,
            message="Screen-action mappings updated successfully",
            data={
                "inserted": len(to_insert),
                "activated": len(to_activate),
                "deactivated": len(to_deactivate)
            }
        )

    except Exception as e:
        return InsertScreenActionMappingResponse(
            status_code=500,
            message=f"Internal server error: {str(e)}",
            data=None
        )

async def insert_role_screen_actions_service(request: Request, payload: InsertRoleScreenActionsRequest):
    """
    Insert/Update/Deactivate role → screen → action mappings.
    Supports multiple screen_action_ids per role.
    """
    try:
        if not payload.items:
            return InsertRoleScreenActionsResponse(
                status_code=400,
                message="No role screen actions provided",
                data=None
            )

        to_insert = []
        to_activate = []
        to_deactivate = []

        for item in payload.items:
            role_id = item.role_id

            # --- 1. Fetch existing mappings for this role ---
            query = """
                SELECT * FROM ai_verify_security.screen_action_mapping_roles
                WHERE role_id = :role_id
            """
            existing_records = await database.fetch_all(query, values={"role_id": role_id})

            existing_map = {rec["screen_action_id"]: rec for rec in existing_records}

            incoming_ids = set(item.screen_action_id)

            # --- 2. Determine insert or activate ---
            for screen_action_id in incoming_ids:
                if screen_action_id not in existing_map:
                    # New mapping → insert
                    to_insert.append({
                        "role_id": role_id,
                        "screen_action_id": screen_action_id,
                        "is_active": True,
                        "created_by": item.created_by
                    })
                else:
                    # Existing but inactive → activate
                    if not existing_map[screen_action_id]["is_active"]:
                        to_activate.append(existing_map[screen_action_id]["screen_action_mapping_role_id"])

            # --- 3. Determine deactivate (soft delete) ---
            for screen_action_id, rec in existing_map.items():
                if screen_action_id not in incoming_ids and rec["is_active"]:
                    to_deactivate.append(rec["screen_action_mapping_role_id"])

        # --- 4. Execute DB operations ---
        if to_insert:
            insert_query = """
                INSERT INTO ai_verify_security.screen_action_mapping_roles
                    (role_id, screen_action_id, is_active, created_by)
                VALUES (:role_id, :screen_action_id, :is_active, :created_by)
            """
            await database.execute_many(insert_query, values=to_insert)

        if to_activate:
            activate_query = """
                UPDATE ai_verify_security.screen_action_mapping_roles
                SET is_active = TRUE
                WHERE screen_action_mapping_role_id = ANY(:ids)
            """
            await database.execute(activate_query, values={"ids": to_activate})

        if to_deactivate:
            deactivate_query = """
                UPDATE ai_verify_security.screen_action_mapping_roles
                SET is_active = FALSE
                WHERE screen_action_mapping_role_id = ANY(:ids)
            """
            await database.execute(deactivate_query, values={"ids": to_deactivate})

        return InsertRoleScreenActionsResponse(
            status_code=200,
            message="Role screen actions updated successfully",
            data={
                "inserted": len(to_insert),
                "activated": len(to_activate),
                "deactivated": len(to_deactivate)
            }
        )

    except Exception as err:
        return InsertRoleScreenActionsResponse(
            status_code=500,
            message=f"Internal server error: {str(err)}",
            data=None
        )


async def get_role_permissions_service(request: Request, user_id: int):
    """
    Fetch role permissions (screens + actions grouped) for a given user_id
    """
    try:
        query = """
            SELECT
                u.user_id,
                u.user_name,
                u.email,
                r.role_id,
                r.role_name,
                s.screen_id,
                s.screen_name,
                a.action_id,
                a.action_name
            FROM ai_verify_transaction.users u
            JOIN ai_verify_transaction.user_role_mapping urm
                ON u.user_id = urm.user_id
            JOIN ai_verify_master.user_roles r
                ON urm.role_id = r.role_id
            JOIN ai_verify_security.screen_action_mapping_roles samr
                ON r.role_id = samr.role_id
            JOIN ai_verify_security.screen_action_mapping sam
                ON samr.screen_action_id = sam.screen_action_id
            JOIN ai_verify_master.screens s
                ON sam.screen_id = s.screen_id
            JOIN ai_verify_master.actions a
                ON sam.action_id = a.action_id
            WHERE u.is_active
              AND urm.is_active 
              AND r.is_active 
              AND sam.is_active 
              AND samr.is_active 
              AND s.is_active 
              AND a.is_active 
              AND u.user_id = :user_id
        """

        rows = await database.fetch_all(query, values={"user_id": user_id})
        if not rows:
            return {"status_code": 404, "message": "No role permissions found", "data": None}

        # Convert rows -> dict
        rows = [dict(r) for r in rows]

        # Extract common info
        user_info = {
            "user_id": rows[0]["user_id"],
            "user_name": rows[0]["user_name"],
            "email": rows[0]["email"],
            "role_id": rows[0]["role_id"],
            "role_name": rows[0]["role_name"],
            "screens": []
        }

        # Group by screen
        screens_dict = {}
        for row in rows:
            sid = row["screen_id"]
            if sid not in screens_dict:
                screens_dict[sid] = {
                    "screen_id": sid,
                    "screen_name": row["screen_name"],
                    "actions": []
                }
            screens_dict[sid]["actions"].append({
                "action_id": row["action_id"],
                "action_name": row["action_name"]
            })

        user_info["screens"] = list(screens_dict.values())

        return {
            "status_code": 200,
            "message": "Fetched role permissions successfully",
            "data": user_info
        }

    except Exception as err:
        import logging
        logging.exception("Error fetching role permissions")
        return {
            "status_code": 500,
            "message": f"Internal server error: {str(err)}",
            "data": None
        }
