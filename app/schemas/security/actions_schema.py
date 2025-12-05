from pydantic import BaseModel
from typing import Optional, List, Union


# ======================
# Request Schemas
# ======================

class ActionBase(BaseModel):
    ActionName: str


class ActionCreate(ActionBase):
    """Schema for creating a new action"""
    pass


class ActionUpdate(ActionBase):
    """Schema for updating an existing action"""
    pass


# ======================
# Response Schemas
# ======================

class ActionResponse(BaseModel):
    ActionId: int
    ActionName: str


class DeleteResponse(BaseModel):
    ActionId: int


# ======================
# Generic Response Wrapper
# ======================

class ResponseModel(BaseModel):
    status_code: int
    message: str
    data: Optional[Union[dict, List[dict]]] = None
