from datetime import datetime

from pydantic import BaseModel,validator
from typing import Optional, List,Union
import json


# class Screen(BaseModel):
#     ScreenId: int
#     ScreenName: str
#     IsActive: bool
#     CreatedBy: int
#     CreatedDate: datetime
#
#
# class ScreenListResponse(BaseModel):
#     status_code: int
#     message: str
#     data: Optional[List[Screen]]


# class Actions(BaseModel):
#     ActionId: int
#     ActionName: str
#
# class ActionListResponse(BaseModel):
#     status_code: int
#     message: str
#     data: Optional[List[Actions]]


#######################################################

class ScreenAction(BaseModel):
    ScreenActionId: int
    ActionId: int
    ActionName: str


class ScreenWithActions(BaseModel):
    ScreenId: int
    ScreenName: str
    actions: List[ScreenAction]


class ScreenActionMappingResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[List[ScreenWithActions]]

##########################################################


class ScreenActionItem(BaseModel):
    screen_id: int
    action_ids: List[int]
    is_active: bool
    created_by: int

class InsertScreenActionMappingRequest(BaseModel):
    items: List[ScreenActionItem]

class InsertScreenActionMappingResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[dict]

#####################################################################

class RoleScreenActionItem(BaseModel):
    role_id: int
    screen_action_id: List[int]
    is_active: bool
    created_by: int



class InsertRoleScreenActionsRequest(BaseModel):
    items: List[RoleScreenActionItem]


class InsertRoleScreenActionsResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[dict]
#####################################################################

class RoleIdRequest(BaseModel):
    role_id: int

class Action(BaseModel):
    Screen_Action_ID: int
    ActionName: str
    active: int

class ScreenActions(BaseModel):
    ScreenId: int
    ScreenName: str
    actions: Union[List[Action], str]  # Accept list or JSON string

    @validator("actions", pre=True)
    def parse_actions(cls, v):
        if isinstance(v, str):
            try:
                # Convert JSON string to list of dicts
                v = json.loads(v)
            except json.JSONDecodeError:
                v = []
        return v
class RoleScreenActionsResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[List[ScreenActions]]


#################################################################

# get_role_permissions_request

class RolePermissionRequest(BaseModel):
    user_id: int


class ActionItem(BaseModel):
    action_id: int
    action_name: str

class ScreenItem(BaseModel):
    screen_id: int
    screen_name: str
    actions: List[ActionItem]

class UserRolePermissions(BaseModel):
    user_id: int
    user_name: str
    email: str
    role_id: int
    role_name: str
    screens: List[ScreenItem]

class RolePermissionResponse(BaseModel):
    status_code: int
    message: str
    data: Optional[UserRolePermissions]
