import logging
from fastapi import APIRouter, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from app.db.database import database
# from app.security import get_current_user
from fastapi import Request
from typing import Union

from app.schemas.transaction.project_schema import DashboardResponse, ProjectDetailResponse, ProjectCreateRequest, ProjectOut, \
    ProjectSummaryListResponse, UpdateProjectDetailsRequest, dashboard_Get_Request
# from app.security import get_current_user
from app.services.transaction.project_service import get_dashboard_data, get_project_detail, create_project_service, \
    get_all_projects_by_user_id, get_all_projects, \
    new_get_all_projects, get_project_details_service, update_project_details_service, delete_project_service
from fastapi import APIRouter, Depends, UploadFile, File
from typing import List, Optional
from fastapi import status


router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])
logger = logging.getLogger(__name__)


@router.get("/project-details/{project_id}")
async def read_project(project_id: int):
    try:
        project: Optional[ProjectDetailResponse] = await get_project_detail(project_id)

        if not project:
            logger.warning(f"Project with id={project_id} not found")
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status_code": status.HTTP_404_NOT_FOUND,
                    "message": "Project not found",
                    "data": None
                }
            )

        logger.info(f"Project details retrieved successfully for project_id={project_id}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status_code": status.HTTP_200_OK,
                "message": "Project details retrieved successfully",
                "data": project.dict()   # convert Pydantic model to dict
            }
        )

    except Exception as e:
        logger.exception(f"Internal error while retrieving project_id={project_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Internal server error",
                "data": None
            }
        )


# @router.get("/project-details/{project_id}")
# async def read_project(project_id: int):
#     try:
#         project = await get_project_detail(project_id)
#
#         # Negative case: project not found
#         if not project:
#             logger.warning(f"Project with id={project_id} not found")
#             raise HTTPException(status_code=404, detail="Project not found")
#
#         # Positive case: wrap in custom response
#         logger.info(f"Project details retrieved successfully for project_id={project_id}")
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "status_code": 200,
#                 "message": "Project details fetched successfully",
#                 "data": project.model_dump()  # convert Pydantic model to dict
#             },
#         )
#
#     except HTTPException as http_ex:
#         raise http_ex
#
#     except Exception as e:
#         logger.exception(f"Internal error while retrieving project_id={project_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")





@router.get("/projects_by_user_id/{user_id}")
async def fetch_all_projects_by_user_id(user_id: int):
    try:
        projects = await get_all_projects_by_user_id(user_id)

        if not projects:
            return JSONResponse(
                status_code=404,
                content={
                    "status_code": 404,
                    "message": f"No projects found for user_id={user_id}",
                    "data": [],
                },
            )

        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "message": "Projects fetched successfully",
                "data": [ProjectOut(**dict(row._mapping)).model_dump() for row in projects],

            },
        )

    except Exception as e:
        logger.exception(f"Error fetching projects for user_id={user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------
@router.post("/createProject")
async def create_project_api(
    request: Request,
    payload: ProjectCreateRequest = Depends(ProjectCreateRequest.as_form),
    files: Optional[List[UploadFile]] = None,
    change_request_file: Union[UploadFile, str, None] = Form(None),
):
    if isinstance(change_request_file, str) and change_request_file.strip() == "":
        change_request_file = None
    return await create_project_service(
        payload=payload,
        files=files,
        change_request_file=change_request_file,
        request=request
    )




@router.get("/getallprojects")
async def get_projects():
    """
    Get all active projects
    """
    return await get_all_projects()

# @router.get("/new_get_all_projects", response_model=ProjectSummaryListResponse)
# async def get_all_projects():
#     """
#     Fetch all active projects with users, phases, and counts.
#     """
#     return await new_get_all_projects()


from fastapi import Request

@router.get("/new_get_all_projects", response_model=ProjectSummaryListResponse)
async def get_all_projects(request: Request):
    user = request.state.user  # from middleware
    print("response:",user)
    role_id = user.get("role_id")
    user_id = 0 if role_id == 1 else user.get("user_id")

    return await new_get_all_projects(user_id)



#
# @router.get("/new_get_all_projects", response_model=ProjectSummaryListResponse)
# async def get_all_projects(current_user: dict = Depends(get_current_user)):
#     """
#     Fetch all active projects.
#     - Admin (role_id = 1) gets all projects (user_id = 0)
#     - Others get their own projects.
#     """
#     role_id = current_user.get("role_id")
#     user_id = 0 if role_id == 1 else current_user.get("user_id")
#
#     return await new_get_all_projects(user_id)



#
# @router.get("/new_get_all_projects", response_model=ProjectSummaryListResponse)
# async def get_all_projects(current_user: dict = Depends(get_current_user)):
#     """
#     Fetch all active projects.
#     - Admin (role_id = 1) gets all projects (user_id = 0)
#     - Others get their own projects.
#     """
#     role_id = current_user.get("role_id")
#     user_id = 0 if role_id == 1 else current_user.get("user_id")
#
#     return await new_get_all_projects(user_id)


# @router.get("/getProjectFile")
# async def get_project_file_api(file_name: str = Query(..., description="Name of the file to retrieve")):
#     return await get_project_file_service(file_name)



@router.get("/retrieve_project_details/{project_id}")                #get_project_details  skr
async def get_project_details(project_id: int):
    return await get_project_details_service(project_id)



@router.put("/update_project_details/{project_id}")
async def update_project_details(
    request: Request,
    project_id: int,
    title:Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    renewal_year: Optional[str] = Form(None),
    make: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    remove_file_ids: Optional[str] = Form(None),
    add_user_ids: Optional[str] = Form(None),
    remove_user_ids: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    change_request_code: Optional[str] = Form(None),
    change_request_file: Union[UploadFile, str, None] = Form(None),
    change_request_json: Optional[str] = Form(None),
    change_request_id: Optional[int] = Form(None),
):
    if isinstance(change_request_file, str) and change_request_file.strip() == "":
        change_request_file = None
    """
    Update project details, optionally handling file uploads/removals and user assignments.
    Accepts multipart/form-data.
    """

    # Parse remove_file_ids, add_user_ids, remove_user_ids from comma-separated strings
    def parse_ids(id_str: Optional[str]) -> Optional[List[int]]:
        if id_str:
            try:
                return [int(i.strip()) for i in id_str.split(",") if i.strip()]
            except ValueError:
                return None
        return None

    parsed_remove_file_ids = parse_ids(remove_file_ids)
    parsed_add_user_ids = parse_ids(add_user_ids)
    parsed_remove_user_ids = parse_ids(remove_user_ids)

    if (remove_file_ids and parsed_remove_file_ids is None) or \
       (add_user_ids and parsed_add_user_ids is None) or \
       (remove_user_ids and parsed_remove_user_ids is None):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid ID format. Use comma-separated integers.",
                "data": None,
            },
        )

    # Call the service
    return await update_project_details_service(
        request=request,
        project_id=project_id,
        title=title,
        description=description,
        start_date=start_date,
        end_date=end_date,
        renewal_year=renewal_year,
        make=make,
        model=model,
        files=files,
        remove_file_ids=parsed_remove_file_ids,
        add_user_ids=parsed_add_user_ids,
        remove_user_ids=parsed_remove_user_ids,
        change_request_code=change_request_code,
        change_request_file=change_request_file,
        change_request_json=change_request_json,
        change_request_id=change_request_id,
    )


@router.delete("/delete_project/{project_id}")
async def delete_project(project_id: int):
    return await delete_project_service(project_id)



@router.get("/get_dashboard_data", response_model=DashboardResponse)
# async def fetch_dashboard_data(payload: dashboard_Get_Request):
#     return await get_dashboard_data(payload)
async def fetch_dashboard_data(
    user_id: int = Query(..., description="User ID"),
    project_id: Optional[int] = Query(None, description="Project ID")
):
    payload = dashboard_Get_Request(user_id=user_id, project_id=project_id)
    return await get_dashboard_data(payload)