import logging
from fastapi import APIRouter,Body,Request,status
from fastapi.responses import JSONResponse
from app.services.risk_assessment_template_service import (
    # get_all_risk_assessment_templates_service, get_risk_assessment_templates_by_asset_type_service,
    get_latest_templates_by_type_service, save_json_template_transaction_service, get_json_template_by_id_service,

)

router = APIRouter(prefix="/master", tags=["Risk Assessment Template"])
logger = logging.getLogger(__name__)





@router.get("/by-template-type", summary="Get latest JSON templates by template_type_id")
async def get_templates_by_template_type(template_type_id: int):
    """
    Fetch the latest version of all JSON templates for a given template_type_id.
    """
    return await get_latest_templates_by_type_service(template_type_id)



@router.post("/save", summary="Save a JSON Template Transaction")
async def save_json_template(
    request: Request,
    template_json: dict = Body(..., description="Template JSON data")
):
    """
    Save a new JSON Template Transaction.
    The `created_by` is automatically taken from the authenticated user token.
    """
    try:
        user = getattr(request.state, "user", None)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"message": "Unauthorized. No user context found."},
            )

        created_by = user.get("user_id")
        return await save_json_template_transaction_service(created_by, template_json)

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": f"Internal server error: {str(e)}"},
        )


@router.get("/json-template/{transaction_template_id}", summary="Get saved JSON Template by ID")
async def get_json_template_by_id(transaction_template_id: int):
    """
    Fetch a saved JSON Template Transaction by its transaction_template_id.
    """
    return await get_json_template_by_id_service(transaction_template_id)
