# UserRoleMappingschema.py


from pydantic import BaseModel
from typing import Optional, List


class UserRoleMappingCreateRequest(BaseModel):
    user_id: int
    role_ids: List[int]
    # is_active: Optional[bool] = True   # default true

class UserRoleMappingResponse(BaseModel):
    user_role_map_id: int
    user_id: int
    role_id: int
    is_active: bool




