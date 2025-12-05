from typing import List
from pydantic import BaseModel
from typing import Optional

class MapUsersToTaskRequest(BaseModel):
    project_task_id: int
    user_ids: List[int]


class UserResponseByTask(BaseModel):
    user_id: int
    user_name: str
    email: str
    image_url: Optional[str] = None
