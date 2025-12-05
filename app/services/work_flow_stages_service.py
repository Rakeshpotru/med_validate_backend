import logging
from fastapi import status
from app.db.database import database
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, update, insert, and_

from app.db.master.work_flow_stages import work_flow_stages_table
from app.db.master.work_flow_stage_phase_mapping import work_flow_stage_phase_mapping_table
from app.db import sdlc_phases_table
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------- CREATE WORKFLOW STAGE ----------------------
async def create_workflow_stage_service(db, payload):
    try:
        query = select(work_flow_stages_table).where(
            func.lower(func.trim(work_flow_stages_table.c.work_flow_stage_name))
            == func.lower(func.trim(payload.work_flow_stage_name))
        )
        existing_work_flow_stage = await database.fetch_one(query)
        
        if existing_work_flow_stage:
            if existing_work_flow_stage.is_active:
                print(existing_work_flow_stage,'existing_work_flow_stage is active ')

                logger.warning(f"Stage '{payload.work_flow_stage_name}' already exists and is active.")
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "status_code": status.HTTP_409_CONFLICT,
                        "message": f"Stage '{payload.work_flow_stage_name}' already exists",
                        "data": []
                    }
                )
            else:
                print(existing_work_flow_stage,'existing_work_flow_stage is not active ')
                # If inactive → Activate it
                update_query = (
                    work_flow_stages_table.update()
                    .where(work_flow_stages_table.c.work_flow_stage_id == existing_work_flow_stage.work_flow_stage_id)
                    .values(is_active=True)
                )
                await database.execute(update_query)

                logger.info(f"Inactive Stage '{payload.work_flow_stage_name}' activated with ID {existing_work_flow_stage.work_flow_stage_id}.")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "status_code": status.HTTP_200_OK,
                        "message": f"Role '{payload.work_flow_stage_name}' activated successfully",
                        "data": {
                            "Stage_id": existing_work_flow_stage.work_flow_stage_id,
                            "stage_name": payload.work_flow_stage_name
                        }
                    }
                )
                
                
        query = insert(work_flow_stages_table).values(
            work_flow_stage_name=payload.work_flow_stage_name,
            is_active=True
        ).returning(work_flow_stages_table.c.work_flow_stage_id)

        stage_id = await database.execute(query)


        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "Workflow stage created successfully", "stage_id": stage_id}
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )


# ---------------------- UPDATE WORKFLOW STAGE ----------------------
async def update_workflow_stage_service(db, stage_id, payload):
    try:
        values = {}
        if payload.work_flow_stage_name is not None:
            values["work_flow_stage_name"] = func.trim(payload.work_flow_stage_name)
        if payload.is_active is not None:
            values["is_active"] = payload.is_active

        query = (
            update(work_flow_stages_table)
            .where(work_flow_stages_table.c.work_flow_stage_id == stage_id)
            .values(values)
        )
        await db.execute(query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Workflow stage updated successfully"}
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )


# ---------------------- DELETE WORKFLOW STAGE ----------------------
async def delete_workflow_stage_service(db, stage_id):
    try:
        query = (
            update(work_flow_stages_table)
            .values(is_active=False)
            .where(work_flow_stages_table.c.work_flow_stage_id == stage_id)
        )
        await db.execute(query)

        # Also disable related mappings
        query_map = (
            update(work_flow_stage_phase_mapping_table)
            .values(is_active=False)
            .where(work_flow_stage_phase_mapping_table.c.work_flow_stage_id == stage_id)
        )
        await db.execute(query_map)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Workflow stage deleted successfully"}
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )


# ---------------------- GET ALL WORKFLOW STAGES ----------------------
async def get_all_workflow_stages_service(db):
    query = select(work_flow_stages_table).order_by(work_flow_stages_table.c.work_flow_stage_id).where(work_flow_stages_table.c.is_active == True)
    data = await database.fetch_all(query)
    result = [dict(row) for row in data]

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": result}
    )


# ---------------- MAP PHASES TO STAGE (CREATE/UPDATE/REMOVE) ----------------
async def map_phases_to_stage_service(db, payload):
    try:
        stage_id = payload.stage_id
        phase_ids = payload.phase_ids
        user_id = payload.user_id
        now = datetime.now()

        # Disable all existing mappings of these phases (any stage)
        disable_old = (
            update(work_flow_stage_phase_mapping_table)
            .where(work_flow_stage_phase_mapping_table.c.sdlc_phase_id.in_(phase_ids))
            .values(is_active=False, updated_by=user_id, updated_date=now)
        )
        await db.execute(disable_old)

        # Disable all mappings of this stage that are NOT in new list
        disable_removed = (
            update(work_flow_stage_phase_mapping_table)
            .where(
                and_(
                    work_flow_stage_phase_mapping_table.c.work_flow_stage_id == stage_id,
                    work_flow_stage_phase_mapping_table.c.sdlc_phase_id.not_in(phase_ids)
                )
            )
            .values(is_active=False, updated_by=user_id, updated_date=now)
        )
        await db.execute(disable_removed)

        # Insert / Reactivate new mappings
        for pid in phase_ids:
            # Check existing mapping
            query = select(work_flow_stage_phase_mapping_table).where(
                and_(
                    work_flow_stage_phase_mapping_table.c.work_flow_stage_id == stage_id,
                    work_flow_stage_phase_mapping_table.c.sdlc_phase_id == pid
                )
            )
            existing = await db.fetch_one(query)

            if existing:
                # Reactivate
                q = (
                    update(work_flow_stage_phase_mapping_table)
                    .where(work_flow_stage_phase_mapping_table.c.work_flow_stage_phase_mapping_id == existing.work_flow_stage_phase_mapping_id)
                    .values(is_active=True, updated_by=user_id, updated_date=now)
                )
                await db.execute(q)
            else:
                # Insert new
                q = insert(work_flow_stage_phase_mapping_table).values(
                    work_flow_stage_id=stage_id,
                    sdlc_phase_id=pid,
                    is_active=True,
                    created_by=user_id,
                    created_date=now
                )
                await db.execute(q)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Stages & phases updated successfully"}
        )

    except Exception as e:
        logger.error(f"Mapping error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"}
        )


# ---------------------- GET PHASES BY STAGE ----------------------
async def get_phases_by_stage_service(db, stage_id):
    query = select(work_flow_stage_phase_mapping_table).where(
        and_(
            work_flow_stage_phase_mapping_table.c.work_flow_stage_id == stage_id,
            work_flow_stage_phase_mapping_table.c.is_active == True
        )
    )
    data = await database.fetch_all(query)

    result = [dict(row) for row in data]
    print(result,'result')
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"data": result}
    )



async def get_stage_phase_mapping_service():
    query = (
        select(
            work_flow_stages_table.c.work_flow_stage_id.label("stage_id"),
            work_flow_stages_table.c.work_flow_stage_name.label("stage_name"),
            sdlc_phases_table.c.phase_id,
            sdlc_phases_table.c.phase_name
        )
        .select_from(
            work_flow_stages_table
            .join(
                work_flow_stage_phase_mapping_table,
                and_(
                    work_flow_stage_phase_mapping_table.c.work_flow_stage_id == work_flow_stages_table.c.work_flow_stage_id,
                    work_flow_stage_phase_mapping_table.c.is_active == True
                )
            )
            .join(
                sdlc_phases_table,
                sdlc_phases_table.c.phase_id == work_flow_stage_phase_mapping_table.c.sdlc_phase_id
            )
        )
        .where(work_flow_stages_table.c.is_active == True)
    )

    rows = await database.fetch_all(query)

    result = {}
    for r in rows:
        sid = r["stage_id"]
        if sid not in result:
            result[sid] = {
                "stage_id": sid,
                "stage_name": r["stage_name"],
                "phases": []
            }
        result[sid]["phases"].append({
            "phase_id": r["phase_id"],
            "phase_name": r["phase_name"]
        })

    return list(result.values())