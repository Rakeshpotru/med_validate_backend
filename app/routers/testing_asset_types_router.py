from fastapi import APIRouter
from app.services.testing_asset_types_service import get_all_testing_asset_types

router = APIRouter(prefix="/master", tags=["Master APIs"])

@router.get("/getAllTestingAssetTypes")
async def get_testing_asset_types():
    return await get_all_testing_asset_types()
