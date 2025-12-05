# app/routers/template_type_router.py
from fastapi import APIRouter, Path, Query,Request

from app.schemas.template_type_schema import (
    CreateJsonTemplate,
    JsonTemplateResponse,
    TemplateVersionsResponse  # Kept for potential use, but not enforced in response_model
)
from app.services.template_type_service import (
    get_all_template_types,
    create_json_template as create_template_service,
    get_json_template_by_id,
    get_all_versions_by_type_id
)

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllTemplateTypes")
async def get_template_types():
    return await get_all_template_types()

@router.post("/createJsonTemplate")
async def create_json_template(request: Request, input: CreateJsonTemplate):
    return await create_template_service(input, request)

@router.get("/getJsonTemplate/{template_id}")
async def get_json_template(
    template_id: int = Path(..., ge=1, description="The ID of the JSON template to retrieve")
):
    return await get_json_template_by_id(template_id)

@router.get("/getAllVersions")
async def get_all_versions(
    template_type_id: int = Query(..., ge=1, description="The template_type_id to filter versions")
):
    return await get_all_versions_by_type_id(template_type_id)