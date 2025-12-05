from pydantic import BaseModel
from typing import Optional, List

class ProjectUser(BaseModel):
    user_id: int
    user_name: str
    image_url: Optional[str] = None
    role_id: Optional[int] = None
    role_name: Optional[str] = None

class ProjectUsersResponse(BaseModel):
    status_code: int
    message: str
    data: List[ProjectUser]
