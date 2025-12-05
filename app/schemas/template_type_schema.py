# app/schemas/template_type_schema.py
from typing import Dict, Any, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class TemplateTypeFullResponse(BaseModel):
    template_type_id: int
    template_type_name: str
    is_active: bool
    template_format_type_id: int
    format_name: str
    section: bool
    weightage: bool
    table: bool

    model_config = ConfigDict(from_attributes=True)  # v2 style

class CreateJsonTemplate(BaseModel):
    template_name: str
    template_type_id: int
    json_template: Dict[str, Any]
    created_by: int  # Assuming user ID; change to str if username

class JsonTemplateResponse(BaseModel):
    template_id: int
    template_name: str
    template_type_id: int
    json_template: Dict[str, Any]
    created_by: int
    created_date: datetime  # Dumps to ISO str with mode='json'
    template_version: float  # ✅ Changed to float to match table/code

    model_config = ConfigDict(from_attributes=True)  # v2 style

# Optional: Wrapper for versions list (not enforced in response_model, but available for future use)
class TemplateVersionsResponse(BaseModel):
    versions: list[JsonTemplateResponse]

    model_config = ConfigDict(from_attributes=True)