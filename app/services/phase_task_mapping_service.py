from fastapi import APIRouter, status
from starlette.responses import JSONResponse
from sqlalchemy import select,and_

from app.db import sdlc_phases_table, sdlc_tasks_table
from app.db.database import database  # Your database connection instance

import logging

from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.schemas.phase_task_mapping_schema import PhaseTaskMappingRequest

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_sdlc_phases_with_tasks():
    try:
        logger.info("Fetching SDLC phases with their mapped tasks")

        # Join and filter only by mapping table's is_active
        query = (
            select(
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name,
                sdlc_tasks_table.c.task_id,
                sdlc_tasks_table.c.task_name
            )
            .select_from(
                sdlc_phase_tasks_mapping_table
                .join(sdlc_phases_table, sdlc_phase_tasks_mapping_table.c.phase_id == sdlc_phases_table.c.phase_id)
                .join(sdlc_tasks_table, sdlc_phase_tasks_mapping_table.c.task_id == sdlc_tasks_table.c.task_id)
            )
            .where(sdlc_phase_tasks_mapping_table.c.is_active == True)  # Only mapping table filter
            .order_by(sdlc_tasks_table.c.order_id)
        )

        rows = await database.fetch_all(query)

        if not rows:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": 404,
                    "message": "No active phase-task mappings found",
                    "data": []
                }
            )

        # Group tasks by phase_id
        phase_task_map = {}
        phase_name_map = {}

        for row in rows:
            pid = row["phase_id"]
            if pid not in phase_task_map:
                phase_task_map[pid] = []
                phase_name_map[pid] = row["phase_name"]

            phase_task_map[pid].append({
                "task_id": row["task_id"],
                "task_name": row["task_name"]
            })

        # Prepare final response list
        data = []
        for pid, tasks in phase_task_map.items():
            data.append({
                "phase_id": pid,
                "phase_name": phase_name_map[pid],
                "tasks": tasks
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "SDLC phases with tasks fetched successfully",
                "data": data
            }
        )

    except Exception as e:
        logger.error(f"Error fetching SDLC phases with tasks: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": 500,
                "message": "Internal server error",
                "data": []
            }
        )


async def map_phase_to_tasks(payload: PhaseTaskMappingRequest):
    try:
        logger.info(f"🟢 Received request to map phase_id={payload.phase_id} with tasks={payload.task_ids}")

        # --- 0. Validate ---
        if not payload.phase_id or payload.phase_id <= 0:
            return JSONResponse(status_code=400, content={"message": "Valid phase_id is required", "data": []})
        if not payload.task_ids or not isinstance(payload.task_ids, list) or not all(isinstance(t, int) for t in payload.task_ids):
            return JSONResponse(status_code=400, content={"message": "Valid task_ids list is required", "data": []})

        phase_id = payload.phase_id
        new_task_ids = payload.task_ids

        # --- 1. Fetch all existing records for this phase ---
        query = select(sdlc_phase_tasks_mapping_table).where(sdlc_phase_tasks_mapping_table.c.phase_id == phase_id)
        existing = await database.fetch_all(query)

        existing_task_ids = [r["task_id"] for r in existing]
        existing_map = {r["task_id"]: r for r in existing}

        # --- 2. Prepare operations ---
        to_insert = []
        to_activate = []

        for tid in new_task_ids:
            if tid not in existing_task_ids:
                to_insert.append({"phase_id": phase_id, "task_id": tid, "is_active": True})
            elif not existing_map[tid]["is_active"]:
                to_activate.append(existing_map[tid]["phase_task_map_id"])

        logger.info(f"🟡 To Insert: {to_insert}")
        logger.info(f"🟢 To Activate: {to_activate}")
        logger.info(f"🔴 Deactivate all others not in: {new_task_ids}")

        # --- 3. Execute all updates safely ---
        async with database.transaction():
            # Insert missing
            if to_insert:
                await database.execute_many(
                    query=sdlc_phase_tasks_mapping_table.insert(),
                    values=to_insert
                )

            # Reactivate inactive ones
            if to_activate:
                activate_query = (
                    sdlc_phase_tasks_mapping_table.update()
                    .where(sdlc_phase_tasks_mapping_table.c.phase_task_map_id.in_(to_activate))
                    .values(is_active=True)
                )
                await database.execute(activate_query)

            # Deactivate any others not selected (covers duplicates too)
            deactivate_query = (
                sdlc_phase_tasks_mapping_table.update()
                .where(
                    and_(
                        sdlc_phase_tasks_mapping_table.c.phase_id == phase_id,
                        sdlc_phase_tasks_mapping_table.c.task_id.notin_(new_task_ids)
                    )
                )
                .values(is_active=False)
            )
            await database.execute(deactivate_query)

        logger.info("✅ Phase to task mapping successfully updated.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": 200,
                "message": "Phase to task mapping updated successfully",
                "data": [],
            },
        )

    except Exception as e:
        logger.error(f"❌ Error updating phase to task mapping: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": 500,
                "message": "Internal server error",
                "data": [],
            },
        )