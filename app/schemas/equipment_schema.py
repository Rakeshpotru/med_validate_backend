from typing import Optional

from pydantic import BaseModel

class EquipmentResponse(BaseModel):
    equipment_id: int
    equipment_name: str
    document_id: Optional[int] = None
    ai_verified_doc: Optional[bool] = None

# ---------- Create Request ----------
class EquipmentCreateRequest(BaseModel):
    equipment_name: str
    # created_by: int
    asset_type_id: int

# ---------- Update Request ----------
class EquipmentUpdateRequest(BaseModel):
    equipment_name: str
    # updated_by: int
    asset_type_id: int


# ---------- Delete Request ----------
class EquipmentDeleteRequest(BaseModel):
    pass