import logging
from fastapi import status
from fastapi.responses import JSONResponse

from app.db import risk_assessment_table, sdlc_phases_table
from app.db.database import database
from app.db.master.risk_sdlcphase_mapping import risk_sdlcphase_mapping_table
from app.schemas.risk_phase_map_schema import RiskPhaseMappingRequest
from sqlalchemy import select

logger = logging.getLogger(__name__)

async def map_risk_to_phases(payload: RiskPhaseMappingRequest):
    try:
        logger.info(f"Start mapping risk_assessment_id to phases")

        # --- 0. Bad Request validation ---
        if not payload.risk_assessment_id or payload.risk_assessment_id <= 0:
            logger.warning("Invalid or missing risk_assessment_id.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Valid risk_assessment_id is required",
                    "data": []
                }
            )

        if not payload.phase_ids or not isinstance(payload.phase_ids, list) or not all(isinstance(p, int) for p in payload.phase_ids):
            logger.warning("Invalid or missing phase_ids list.")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "message": "Valid phase_ids is required",
                    "data": []
                }
            )

        # --- 1. Fetch all existing mappings for this risk_assessment_id ---
        query = select(risk_sdlcphase_mapping_table).where(
            risk_sdlcphase_mapping_table.c.risk_assessment_id == payload.risk_assessment_id
        )
        existing_records = await database.fetch_all(query)

        existing_map = {
            (rec["risk_assessment_id"], rec["phase_id"]): rec for rec in existing_records
        }

        to_insert = []
        to_activate = []
        to_deactivate = []

        # --- 2. Handle Insert / Reactivate / Skip ---
        for phase_id in payload.phase_ids:
            key = (payload.risk_assessment_id, phase_id)
            if key not in existing_map:
                to_insert.append({
                    "risk_assessment_id": payload.risk_assessment_id,
                    "phase_id": phase_id,
                    "is_active": True
                })
            else:
                if not existing_map[key]["is_active"]:
                    to_activate.append(existing_map[key]["risk_phase_map_id"])

        # --- 3. Handle Deactivate ---
        for key, rec in existing_map.items():
            if rec["phase_id"] not in payload.phase_ids and rec["is_active"]:
                to_deactivate.append(rec["risk_phase_map_id"])

        # --- 4. Execute DB operations ---
        if to_insert:
            await database.execute_many(
                query=risk_sdlcphase_mapping_table.insert(),
                values=to_insert
            )

        if to_activate:
            update_query = (
                risk_sdlcphase_mapping_table.update()
                .where(risk_sdlcphase_mapping_table.c.risk_phase_map_id.in_(to_activate))
                .values(is_active=True)
            )
            await database.execute(update_query)

        if to_deactivate:
            update_query = (
                risk_sdlcphase_mapping_table.update()
                .where(risk_sdlcphase_mapping_table.c.risk_phase_map_id.in_(to_deactivate))
                .values(is_active=False)
            )
            await database.execute(update_query)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Risk to phase mapping updated successfully",
                "data": []
            }
        )

    except Exception as e:
        logger.error(f"Error updating risk to phase mapping: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )


async def get_all_risks_with_phases_only_from_mapping():
    try:
        logger.info("Start to fetching risks with mappings phases.")

        # 1. Get all risk-phase mappings with is_active=True (only check in mapping table)
        mappings_query = (
            select(
                risk_sdlcphase_mapping_table.c.risk_assessment_id,
                risk_assessment_table.c.risk_assessment_name,
                sdlc_phases_table.c.phase_id,
                sdlc_phases_table.c.phase_name
            )
            .select_from(
                risk_sdlcphase_mapping_table
                .join(risk_assessment_table, risk_sdlcphase_mapping_table.c.risk_assessment_id == risk_assessment_table.c.risk_assessment_id)
                .join(sdlc_phases_table, risk_sdlcphase_mapping_table.c.phase_id == sdlc_phases_table.c.phase_id)
            )
            .where(risk_sdlcphase_mapping_table.c.is_active == True)
        )

        mappings = await database.fetch_all(mappings_query)

        if not mappings:
            logger.warning("No active mappings found in mapping table.")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "No active risk-phase mappings found",
                    "data": []
                }
            )

        # 2. Group phases by risk_id
        risk_phase_map = {}
        risk_name_map = {}
        for m in mappings:
            rid = m["risk_assessment_id"]
            if rid not in risk_phase_map:
                risk_phase_map[rid] = []
                risk_name_map[rid] = m["risk_assessment_name"]

            risk_phase_map[rid].append({
                "phase_id": m["phase_id"],
                "phase_name": m["phase_name"]
            })

        # 3. Build final response
        data = []
        for rid, phases in risk_phase_map.items():
            data.append({
                "risk_assessment_id": rid,
                "risk_assessment_name": risk_name_map[rid],
                "phases": phases
            })

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Risks with active phases fetched successfully",
                "data": data
            }
        )

    except Exception as e:
        logger.error(f"Error fetching risks with active phases from mapping table: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": []
            }
        )