from fastapi import APIRouter

from app.schemas.equipment_schema import EquipmentUpdateRequest, EquipmentCreateRequest, EquipmentDeleteRequest
from app.services.equipment_service import get_all_equipments, update_equipment, create_equipment, delete_equipment
from fastapi import Request
router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/equipments")
async def fetch_all_equipments():
    return await get_all_equipments()


@router.post("/create-equipments")
async def add_equipment(payload: EquipmentCreateRequest, request: Request):
    return await create_equipment(
        name=payload.equipment_name,
        asset_type_id=payload.asset_type_id,
        request=request
    )

@router.put("/update-equipments/{equipment_id}")
async def modify_equipment(equipment_id: int, payload: EquipmentUpdateRequest, request: Request):
    return await update_equipment(
        equipment_id=equipment_id,
        name=payload.equipment_name,
        asset_type_id=payload.asset_type_id,
        request=request
    )

@router.delete("/delete-equipments/{equipment_id}")
async def remove_equipment(equipment_id: int, request: Request):
    return await delete_equipment(
        equipment_id=equipment_id,
        request=request
    )


