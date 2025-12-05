from typing import List, Optional
from pydantic import BaseModel



class SaveProjectTaskDocumentRequest(BaseModel):
    project_task_id: int
    document_json: str
    created_by: int

class SubmitProjectTaskDocumentRequest(BaseModel):
    project_task_id: int
    document_json: str
    task_status_id: int
    updated_by: int
    
class ProjectFileItem(BaseModel):
    task_doc_id: int
    file_name: str

class taskDocumentsResponse(BaseModel):
    # project_id: int
    phase_id: int
    task_id: int
    project_files: Optional[List[ProjectFileItem]] = None