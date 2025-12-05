from pydantic import BaseModel, Field
from typing import List, Optional

# ------get worklog responses--------
# class TaskWorkLogDetail(BaseModel):
#     task_work_log_id: int
#     user_id: int
#     user_name: Optional[str]
#     image_url: Optional[str]
#     remarks: Optional[str]
#     created_date: Optional[str]
#
# class TaskWorkLogResponse(BaseModel):
#     project_task_id: int
#     task_id: int
#     task_name: Optional[str]
#     task_status_id: Optional[int]
#     status_name: Optional[str]
#     project_phase_id: Optional[int]
#     project_id: Optional[int]
#     phase_id: Optional[int]
#     project_name: Optional[str]
#     phase_name: Optional[str]
#     users: List[dict]
#     work_logs: List[TaskWorkLogDetail]

# -----post worklog-------
class TaskWorkLogCreateRequest(BaseModel):
    project_task_id: int
    user_id: int
    remarks: Optional[str] = None
#
# class TaskWorkLogCreateResponse(BaseModel):
#     task_work_log_id: int
#     project_task_id: int
#     user_id: int
#     remarks: Optional[str]
#     created_date: Optional[str]

class UpdateProjectTaskStatusRequest(BaseModel):
    project_task_id: int = Field(..., description="ID of the project task to update")
    task_status_id: int = Field(..., description="New status ID to be set for the project task")
