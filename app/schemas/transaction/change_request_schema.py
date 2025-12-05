from pydantic import BaseModel
from typing import Optional

class ChangeRequestResponse(BaseModel):
    change_request_id: int
    change_request_code: str
    change_request_file: str
    reject_reason: Optional[str] = None
    project_id: int
    project_name: str
    is_verified: Optional[bool] = None
    transaction_template_id: Optional[int] = None
    change_request_json: Optional[dict] = None

class ChangeRequestVerifyUpdateRequest(BaseModel):
    change_request_id: int
    verified_by: int
    is_verified: bool
    reject_reason: Optional[str] = None
    change_request_user_mapping_id: int
    change_request_json: Optional[dict] = None
