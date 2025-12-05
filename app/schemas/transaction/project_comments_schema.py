# schema Project_Comment_schema

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCommentCreateRequest(BaseModel):
    # project_id: int
    # project_phase_id: Optional[int] = None
    project_task_id: Optional[int] = None
    description: str
    commented_by: int
    is_direct_comment: Optional[bool] = True



class ProjectCommentResponse(BaseModel):
    comment_id: int
    project_id: int
    project_phase_id: Optional[int]
    project_task_id: Optional[int]
    description: str
    commented_by: int
    comment_date: datetime
    is_resolved: bool
    is_direct_comment: bool
    # resolved_by:int
    # resolved_date: datetime


class CommentReplyCreateRequest(BaseModel):
    comment_id: int
    reply_description: str
    replied_by: int
    # replied_date: Optional[datetime] = None   # auto now if not provided


class CommentReplyResponse(BaseModel):
    reply_id: int
    comment_id: int
    reply_description: str
    replied_by: int
    replied_date: datetime




class CommentResolveRequest(BaseModel):
    user_id: int  # Who is resolving the comment

class CommentResolveResponse(BaseModel):
    comment_id: int
    is_resolved: bool
    resolved_by: Optional[int]
    resolved_date: Optional[datetime]
    message: str


# Updating comments schema
class CommentUpdateRequest(BaseModel):
    comment_id: int
    description: str
    updated_by: int


# Updating Reply Comments schema
class ReplyUpdateRequest(BaseModel):
    reply_id: int
    reply_description: str
    updated_by: int   # user who edits the reply
    
class RevertBackRequest(BaseModel):
    task_id: int
    document_json: str