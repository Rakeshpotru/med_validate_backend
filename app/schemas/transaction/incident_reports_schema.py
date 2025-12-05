from pydantic import BaseModel
from typing import Optional,Any

class IncidentCreateRequest(BaseModel):
    incident_type_id: int
    project_task_id: int
    test_script_name: Optional[str]
    testcase_number: Optional[str]
    incident_comment: Optional[str]
    raised_by: int
    document: Optional[str]
    

class IncidentRaiseRequest(BaseModel):
    incident_report_id: Optional[int] = 0
    project_task_id: int
    raised_by: int
    document: Optional[Any]
    

class IncidentResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[dict]
    

class IncidentResolveRequest(BaseModel):
    incident_report_id: int
    resolved_by: int
    resolve_comment: str
    
    
class RaiseIncidentOut(BaseModel):
    incident_report_id: int
    project_id: Optional[int]
    project_name: Optional[str]
    phase_id: Optional[int]
    phase_name: Optional[str]
    task_id: Optional[int]
    task_name: Optional[str]
    test_script_name: Optional[str]
    testcase_number: Optional[str]
    document: Optional[str]
    raise_comment: Optional[str]
    resolve_comment: Optional[str]
    is_resolved: Optional[bool]
    raised_by: Optional[int]
    raised_date: Optional[str]
    resolved_by: Optional[int]
    resolved_date: Optional[str]
    failure_type: Optional[str]
    assigned_to: Optional[int]


class IncidentFetchRequest(BaseModel):
    user_id: Optional[int] = None
    project_id: Optional[int] = None