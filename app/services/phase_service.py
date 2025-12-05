import logging
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, func

from app.db.database import database
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.master.risk_sdlcphase_mapping import risk_sdlcphase_mapping_table
from app.db.master.equipment_ai_docs import equipment_ai_docs_table
from app.schemas.phase_schema import PhaseResponse, PhaseCreateRequest, PhaseUpdateRequest, PhaseDeleteRequest

logger = logging.getLogger(__name__)

# ----------------------
# Phase Services
# ----------------------

async def get_all_phases():
    try:
        logger.info("Fetching all active SDLC phases.")
        query = select(sdlc_phases_table).where(sdlc_phases_table.c.is_active == True).order_by(sdlc_phases_table.c.order_id.asc())
        rows = await database.fetch_all(query)

        if not rows:
            logger.info("No active phases found.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"status_code": 404, "message": "No phases found", "data": []}
            )

        result = [PhaseResponse(**row) for row in rows]
        logger.info("Phases fetched successfully.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status_code": 200, "message": "phases fetched successfully", "data": [r.dict() for r in result]}
        )

    except Exception as e:
        logger.error(f"Error fetching phases: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": 500, "message": "Internal server error", "data": []}
        )


async def create_phase(payload: PhaseCreateRequest):
    try:
        logger.info(f"Creating SDLC phase: {payload.phase_name}")

        if not payload.phase_name or not payload.phase_name.strip():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"status_code": 400, "message": "Phase name is required", "data": []}
            )

        # Check existing phase by name
        name_query = select(sdlc_phases_table).where(func.lower(sdlc_phases_table.c.phase_name) == payload.phase_name.lower())
        existing_phase = await database.fetch_one(name_query)

        if existing_phase:
            if existing_phase.is_active:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"status_code": 409, "message": f"Phase '{payload.phase_name}' already exists", "data": []}
                )
            else:
                # Activate inactive phase
                update_query = sdlc_phases_table.update().where(sdlc_phases_table.c.phase_id == existing_phase.phase_id).values(is_active=True)
                await database.execute(update_query)
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"status_code": 200, "message": f"Phase '{payload.phase_name}' activated successfully",
                             "data": {"phase_id": existing_phase.phase_id, "phase_name": payload.phase_name}}
                )

        # Check duplicate order_id
        order_conflict_query = select(sdlc_phases_table).where(
            and_(sdlc_phases_table.c.order_id == payload.order_id, sdlc_phases_table.c.is_active == True)
        )
        if await database.fetch_one(order_conflict_query):
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={"status_code": 409, "message": f"order_id '{payload.order_id}' already exists for another phase", "data": []}
            )

        # Insert new phase
        insert_query = sdlc_phases_table.insert().values(
            phase_name=payload.phase_name, order_id=payload.order_id, is_active=payload.is_active
        )
        new_phase_id = await database.execute(insert_query)
        logger.info(f"Phase '{payload.phase_name}' created with ID {new_phase_id}.")

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"status_code": 201, "message": "Phase created successfully",
                     "data": {"phase_id": new_phase_id, "phase_name": payload.phase_name, "order_id": payload.order_id}}
        )

    except Exception as e:
        logger.error(f"Error creating phase: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status_code": 500, "message": "Internal server error", "data": []}
        )


async def update_phase(payload: PhaseUpdateRequest):
    try:
        logger.info(f"Updating phase ID {payload.phase_id}")

        if not payload.phase_id:
            return JSONResponse(status_code=400, content={"status_code": 400, "message": "Phase ID is required", "data": []})
        if not payload.phase_name or not payload.phase_name.strip():
            return JSONResponse(status_code=400, content={"status_code": 400, "message": "Phase name is required", "data": []})

        existing_phase = await database.fetch_one(select(sdlc_phases_table).where(sdlc_phases_table.c.phase_id == payload.phase_id))
        if not existing_phase:
            return JSONResponse(status_code=404, content={"status_code": 404, "message": "Phase not found", "data": []})

        # Check name conflict
        name_conflict = await database.fetch_one(
            select(sdlc_phases_table).where(
                and_(func.lower(sdlc_phases_table.c.phase_name) == payload.phase_name.lower(),
                     sdlc_phases_table.c.phase_id != payload.phase_id,
                     sdlc_phases_table.c.is_active == True)
            )
        )
        if name_conflict:
            return JSONResponse(status_code=409, content={"status_code": 409, "message": f"Phase name '{payload.phase_name}' already exists", "data": []})

        # Check order_id conflict
        order_conflict = await database.fetch_one(
            select(sdlc_phases_table).where(
                and_(sdlc_phases_table.c.order_id == payload.order_id,
                     sdlc_phases_table.c.phase_id != payload.phase_id,
                     sdlc_phases_table.c.is_active == True)
            )
        )
        if order_conflict:
            return JSONResponse(status_code=409, content={"status_code": 409, "message": f"order_id '{payload.order_id}' already exists for another phase", "data": []})

        # Update phase
        await database.execute(
            sdlc_phases_table.update()
            .where(sdlc_phases_table.c.phase_id == payload.phase_id)
            .values(phase_name=payload.phase_name, order_id=payload.order_id)
        )

        logger.info(f"Phase ID {payload.phase_id} updated successfully.")
        return JSONResponse(status_code=200, content={
            "status_code": 200, "message": "Phase updated successfully",
            "data": {"phase_id": payload.phase_id, "phase_name": payload.phase_name, "order_id": payload.order_id}
        })

    except Exception as e:
        logger.error(f"Error updating phase: {e}")
        return JSONResponse(status_code=500, content={"status_code": 500, "message": "Internal server error", "data": []})


async def delete_phase(payload: PhaseDeleteRequest):
    try:
        logger.info(f"Deleting phase ID {payload.phase_id}")

        if not payload.phase_id:
            return JSONResponse(status_code=400, content={"status_code": 400, "message": "phase ID is required", "data": []})

        existing_phase = await database.fetch_one(select(sdlc_phases_table).where(sdlc_phases_table.c.phase_id == payload.phase_id))
        if not existing_phase:
            return JSONResponse(status_code=404, content={"status_code": 404, "message": "phase not found", "data": []})
        if not existing_phase.is_active:
            return JSONResponse(status_code=409, content={"status_code": 409, "message": "phase is already inactive", "data": []})

        # Check active mappings
        if await database.fetch_one(select(sdlc_phase_tasks_mapping_table).where(
            (sdlc_phase_tasks_mapping_table.c.phase_id == payload.phase_id) &
            (sdlc_phase_tasks_mapping_table.c.is_active == True))):
            return JSONResponse(status_code=409, content={"status_code": 409, "message": "phase is actively mapped to a task and cannot be inactivated", "data": []})

        if await database.fetch_one(select(risk_sdlcphase_mapping_table).where(
            (risk_sdlcphase_mapping_table.c.phase_id == payload.phase_id) &
            (risk_sdlcphase_mapping_table.c.is_active == True))):
            return JSONResponse(status_code=409, content={"status_code": 409, "message": "phase is actively mapped in risk assessments and cannot be inactivated", "data": []})

        if await database.fetch_one(select(equipment_ai_docs_table).where(
            equipment_ai_docs_table.c.phase_id == payload.phase_id)):
            return JSONResponse(status_code=409, content={"status_code": 409, "message": "phase is actively mapped in equipment AI documents and cannot be inactivated", "data": []})

        # Mark inactive
        await database.execute(
            sdlc_phases_table.update().where(sdlc_phases_table.c.phase_id == payload.phase_id).values(is_active=False)
        )

        logger.info(f"Phase ID {payload.phase_id} inactivated successfully.")
        return JSONResponse(status_code=200, content={"status_code": 200, "message": "phase inactivated successfully", "data": {"phase_id": payload.phase_id, "is_active": False}})

    except Exception as e:
        logger.error(f"Error deleting phase: {e}")
        return JSONResponse(status_code=500, content={"status_code": 500, "message": "Internal server error", "data": []})
