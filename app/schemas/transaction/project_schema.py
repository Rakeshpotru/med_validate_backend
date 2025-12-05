from datetime import datetime, date
from pydantic import BaseModel, field_serializer, Field
from typing import List, Optional, Any
from fastapi import Form, UploadFile, File
from datetime import date
import json

class UserInfo(BaseModel):
    user_id: int
    user_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None


class UserData(BaseModel):
    user_id: int
    user_name: str


class TaskInfo(BaseModel):
    task_id: int
    task_name: str
    status_id: int
    task_users: Optional[List[UserData]] = None


class PhaseInfo(BaseModel):
    phase_id: int
    # phase_id: int
    phase_name: str
    status_id: int
    phase_users: Optional[List[UserData]] = None
    tasks: List[TaskInfo]
    task_docs: Optional[List[dict]] = None

class ProjectDetailResponse(BaseModel):
    project_id: int
    project_name: str
    description: Optional[str]
    risk_assessment_id: int
    risk_assessment_name: str
    created_date: datetime
    status_id: int
    users: List[UserInfo]
    phases: List[PhaseInfo]
    project_files: Optional[List[str]] = None

    @field_serializer("created_date")
    def serialize_date(self, value: datetime) -> str:
        return value.date().isoformat()


class ProjectCreateRequest(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    risk_assessment_id: int
    equipment_id: Optional[int] = None
    # created_by: int
    user_ids: List[int]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    phase_ids: List[int]
    change_request_code: str
    change_request_json: Optional[Any] = None
    # Added fields
    renewal_year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[int] = None  # Changed to int per request
    json_template_id: Optional[int] = None  # <-- Added field here


    @classmethod
    def as_form(
        cls,
        project_name: str = Form(...),
        project_description: Optional[str] = Form(None),
        risk_assessment_id: int = Form(...),
        equipment_id: Optional[int] = Form(None),
        # created_by: int = Form(...),
        user_ids: str = Form(...),  # e.g. "1,2,3"
        start_date: str = Form(..., description="Start date in YYYY-MM-DD format"),
        end_date: Optional[str] = Form(None, description="End date in YYYY-MM-DD format"),
        phase_ids: str = Form(...),  # e.g. "1,2,3"
        change_request_code: str = Form(...),
        change_request_json: Optional[str] = Form(None),
        # Added fields
        renewal_year: Optional[int] = Form(None),
        make: Optional[str] = Form(None),
        model: Optional[int] = Form(None),  # Changed to int per request
        json_template_id: Optional[int] = Form(None),  # <-- Added here too

    ):
        user_ids_list = [int(uid.strip()) for uid in user_ids.split(",") if uid.strip()]
        phase_ids_list = [int(pid.strip()) for pid in phase_ids.split(",") if pid.strip()]
        parsed_json = None
        if change_request_json:
            try:
                parsed_json = json.loads(change_request_json)
            except json.JSONDecodeError:
                parsed_json = change_request_json
        return cls(
            project_name=project_name,
            project_description=project_description,
            risk_assessment_id=risk_assessment_id,
            equipment_id=equipment_id,
            # created_by=created_by,
            user_ids=user_ids_list,
            phase_ids=phase_ids_list,
            start_date=date.fromisoformat(start_date),
            end_date=date.fromisoformat(end_date) if end_date else None,
            change_request_code=change_request_code,
            change_request_json=parsed_json,
            renewal_year=renewal_year,
            make=make,
            model=model,
            json_template_id=json_template_id,  # <-- Added mapping

        )

class ProjectOut(BaseModel):
    project_id: int
    project_name: str
    project_description: Optional[str] = None
    created_date: datetime
    status_id: int
    status_name: Optional[str] = None
    risk_assessment_id: int
    risk_assessment_name: Optional[str] = None
    equipment_id: int
    equipment_name: Optional[str] = None

    @field_serializer("created_date")
    def serialize_date(self, value: datetime) -> str:
        return value.date().isoformat()

# Wrapper response schema
class ProjectsByUserResponse(BaseModel):
    status_code: int
    message: str
    data: List[ProjectOut]

# ------new-----------
class ProjectUserResponse(BaseModel):
    user_id: int
    user_name: str
    user_image: str


class ProjectResponse(BaseModel):
    project_id: int
    project_name: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    days_left: Optional[int]
    completed_percentage: Optional[int]
    users: List[ProjectUserResponse]
# ---------------------



# --------------------------------
# new_get_all_projects
# ----------------------
class ProjectUserInfo(BaseModel):
    user_id: int
    user_name: str
    user_image: str

class ProjectPhaseInfo(BaseModel):
    phase_id: int
    phase_code: str

class ProjectInfo(BaseModel):
    project_id: int
    project_name: str
    start_date: datetime | None
    end_date: datetime | None
    days_left: int | None
    completed_percentage: int | None
    users: List[ProjectUserInfo]
    phases: List[ProjectPhaseInfo] | None
    comments_count: int
    incident_count: int
    file_count: int

class ProjectSummaryListResponse(BaseModel):
    status_code: int
    message: str
    data: List[ProjectInfo]

# -----new------------
class ProjectDetailUserResponse(BaseModel):
    user_id: int
    user_name: str
    image_url: Optional[str]

class ProjectDetailTaskResponse(BaseModel):
    project_task_id: int
    task_id: Optional[int] = None
    task_name: Optional[str] = None
    task_status_id: Optional[int] = None
    task_status_name: Optional[str] = None
    task_users: List[ProjectDetailUserResponse]

class ProjectDetailTaskDocResponse(BaseModel):
    task_doc_id: int
    doc_version: str

class ProjectDetailPhaseResponse(BaseModel):
    project_phase_id: int
    phase_id: int
    phase_name: str
    phase_status_id: Optional[int]
    phase_status_name: Optional[str]
    phase_users: List[ProjectDetailUserResponse]
    tasks: List[ProjectDetailTaskResponse]
    task_docs: List[ProjectDetailTaskDocResponse]

class ProjectDetailFileResponse(BaseModel):
    project_file_id: int
    file_name: str

class ProjectDetailsResponse(BaseModel):
    project_id: int
    project_name: str
    project_description: Optional[str]
    risk_assessment_id: Optional[int]
    risk_assessment_name: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    left_days: Optional[int]
    project_status_id: Optional[int]
    project_status_name: Optional[str]
    completed_percentage: Optional[int] = 0
    users: List[ProjectDetailUserResponse]
    phases: List[ProjectDetailPhaseResponse]
    project_files: List[ProjectDetailFileResponse]


    # Pydantic v2 field serializers for date
    @field_serializer("start_date")
    def serialize_start_date(self, value: datetime) -> Optional[str]:
        return value.date().isoformat() if value else None

    @field_serializer("end_date")
    def serialize_end_date(self, value: datetime) -> Optional[str]:
        return value.date().isoformat() if value else None


# get_project_details is used for binding data on the edit screen.

class ProjectDetailsResponse(BaseModel):
    project_id: int
    project_name: str
    project_description: Optional[str]
    risk_assessment_id: int
    risk_assessment_name: Optional[str]
    equipment_id: Optional[int]
    equipment_name: Optional[str]
    asset_type_id: Optional[int]  # Added
    asset_type_name: Optional[str]  # Added
    created_by: int
    created_by_name: Optional[str]
    created_date: str  # Changed to str for ISO format
    start_date: Optional[str]  # Changed to str
    end_date: Optional[str]  # Changed to str
    status_id: int
    is_active: bool
    users: List[dict]  # e.g., {"user_id": int, "user_name": str}
    files: List[dict]  # e.g., {"file_id": int, "file_name": str}




# # update_project_details API is used to update project details.
#
# class UpdateProjectDetailsRequest(BaseModel):
#     title: str
#     description: Optional[str] = None
#     start_date: Optional[str] = None
#     end_date: Optional[str] = None          # <-- Add end_date here
#     users: Optional[List[int]] = None
#     # files: Optional[List[str]] = None  # List of file names to associate/replace
#
#
# class ProjectDetailsResponse(BaseModel):
#     title: str
#     description: Optional[str]
#     start_date: Optional[str]
#     end_date: Optional[str]                  # <-- Add end_date here
#     users: List[dict]  # e.g., {"user_id": int, "user_name": str}
#     files: List[dict]  # e.g., {"file_id": int, "file_name": str}



class UpdateProjectDetailsRequest(BaseModel):
    title: Optional[str] = None  # Made optional to match endpoint behavior
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    updated_by: Optional[int] = None

class ProjectDetailsResponse(BaseModel):
    title: str
    description: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    files: List[dict]
    users: List[int]  # Added to match response
    
class Task(BaseModel):
    task_id: int
    task_name: str
    status: str
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    due_date: Optional[str] = None

class Phase(BaseModel):
    phase_id: int
    phase_name: str
    sequence: Optional[int] = None
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    tasks: List[Task]

class Project(BaseModel):
    project_id: int
    project_name: str
    status: Optional[str] = None
    is_active: Optional[bool] = None
    total_phases: Optional[int] = None
    completed_phases: Optional[int] = None
    pending_phases: Optional[int] = None
    total_tasks: Optional[int] = None
    completed_tasks: Optional[int] = None
    pending_tasks: Optional[int] = None
    completion_percent: Optional[float] = None
    phases: List[Phase]

class DashboardResponse(BaseModel):
    projects: List[Project]
    
class dashboard_Get_Request(BaseModel):
    user_id: int
    project_id: Optional[int] = None
