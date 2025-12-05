from pydantic import BaseModel

class TestingAssetTypeResponse(BaseModel):
    asset_id: int
    asset_name: str
    is_active: bool
