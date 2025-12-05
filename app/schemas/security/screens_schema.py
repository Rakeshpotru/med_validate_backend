from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Screen(BaseModel):
    ScreenId: int
    ScreenName: str
    IsActive: bool
    CreatedBy: int
    CreatedDate: datetime
    UpdatedBy: Optional[int] = None
    UpdatedDate: Optional[datetime] = None

class ScreenCreateRequest(BaseModel):
    ScreenName: str
    # CreatedBy: int

class ScreenUpdateRequest(BaseModel):
    ScreenName: str
    # UpdatedBy: int

class ScreenListResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[List[Screen]]

class ScreenResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[Screen]
