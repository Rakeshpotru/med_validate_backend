from ast import List
from typing import Optional
from fastapi import APIRouter
from fastapi.params import Query
from app.schemas.transaction.incident_reports_schema import IncidentCreateRequest, IncidentFetchRequest, IncidentRaiseRequest, IncidentResponse, IncidentResolveRequest, RaiseIncidentOut
from app.services.incident_report_service import create_incident_report, fetch_incident_reports, get_task_incident_reports, raise_incident_report, \
    resolve_incident_report, get_incident_reports
from app.db.database import database  # your Database instance

router = APIRouter(prefix="/transaction", tags=["Transaction APIs"])


@router.post("/AddIncidentReport", response_model=IncidentResponse)
async def add_incident_report_api(incident: IncidentCreateRequest):
    async with database.transaction():
        return await create_incident_report(database, incident)
    
    
@router.post("/ResolveIncidentReport", response_model=IncidentResponse)
async def resolve_incident_report_api(request: IncidentResolveRequest):
    async with database.transaction():
        return await resolve_incident_report(
            database, request.incident_report_id, request.resolved_by, request.resolve_comment
        )

@router.get("/GetIncidentReports", response_model=list[RaiseIncidentOut])
async def get_incident_reports_api(
    user_id: Optional[int] = Query(None),
    task_id: Optional[int] = Query(None),
    raised_by: Optional[int] = Query(None),
):
    async with database.transaction():
        return await fetch_incident_reports(database, user_id, task_id, raised_by)


@router.get("/incident-reports/{user_id}")
async def fetch_incident_reports(user_id: int, project_id: int):
    return await get_incident_reports(user_id=user_id, project_id=project_id)

@router.get("/task-incident-reports/{task_id}")
async def get_task_incident_report(task_id: int):
    return await get_task_incident_reports(task_id=task_id)

@router.post("/raise-incident-Report")
async def raise_incidents_report(incident: IncidentRaiseRequest):
    async with database.transaction():
        return await raise_incident_report(database, incident)
    
    
@router.get("/incident-reports")
async def fetch_incident_reports(
    user_id: int | None = Query(None),
    project_id: int | None = Query(None)
):
    print('fetching data for user - router file ${user_id}')
    
    return await get_incident_reports(db=database, user_id=user_id, project_id=project_id)