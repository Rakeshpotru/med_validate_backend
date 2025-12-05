import os

from fastapi import FastAPI, HTTPException
import logging
from fastapi.exception_handlers import http_exception_handler
from contextlib import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.logging_conf import configure_logging
from asgi_correlation_id import CorrelationIdMiddleware
from app.db.database import database
from prometheus_fastapi_instrumentator import Instrumentator

from app.middleware.auth_middleware import auth_middleware
from app.routers.risk_assessment_template_router import router as  risk_assessment_template_router
from app.routers.transaction.projects_router import router as projects_router
# from app.routers.auth import auth_router
from app.routers.work_flow_stages_router import router as  work_flow_stages_router
from app.routers.forgot_password import router as forgot_password
from app.routers.change_password import router as change_password_router
from app.routers.incident_report_router import router as incident_report_router
from app.routers.phase_task_mapping_router import router as phase_task_mapping_router
from app.routers.equipment_router import router as equipment_router
from app.routers.risk_assessment_router import router as  risk_assessment_router
from app.routers.transaction.task_work_log_router import router as task_work_log_router
from app.routers.user_roles_router import router as user_roles_router
from app.routers.status_router import router as status_router
from app.routers.task_router import router as task_router
from app.routers.phase_router import router as phase_router
from app.routers.risk_phase_map_router import router as risk_phase_map_router
from app.routers.transaction.users_router import router as users_router
from app.routers.transaction.project_router import router as project_router
from app.routers.transaction.task_router import router as project_task_router
from app.routers.transaction.project_phase_router import router as project_phase_router
from app.routers.transaction.t_users_router import router as t_users_router
from app.routers.transaction.project_task_router import router as project_map_task_router
from app.routers.docs.task_docs_router import router as project_task_docs
from app.routers.login_router import router as login_router
from app.routers.transaction.user_role_mapping_router import router as user_role_mapping
from app.routers.transaction.project_comments_router import router as project_comments_router
from app.routers.websocket import router as websocket_router
from app.routers.security.roles_screen_router import router as roles_screen_router
from app.routers.security.action_router import router as action_screen_router
from app.routers.security.screens_router import router as screens_router
from app.routers.transaction.file_upload_routes import router as file_upload_routes
from app.routers.docs.task_doc_pdf_route import router as task_doc_pdf_route
from starlette.middleware.sessions import SessionMiddleware
# from app.routers.user_registration import router as user_registration
from app.routers.testing_asset_types_router import router as testing_asset_types_router
from app.routers.transaction.change_request_router import router as change_request_router
from app.routers.transaction.project_details_router import router as project_details_router
# from app.routers.transaction.user_registeration_router import router as user_registration
from app.routers.template_type_router import router as template_type_router
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan, root_path="/api", title="AI Verify Dev")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Add SessionMiddleware (required for Okta OAuth flow)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("DEV_SECRET_KEY", "super-secret-session-key"),  # Use your env secret
    same_site="lax",
    https_only=False,  # set True in production
)

app.add_middleware(CorrelationIdMiddleware)

app.middleware("http")(auth_middleware)

app.include_router(user_roles_router)
app.include_router(status_router)
app.include_router(task_router)
app.include_router(phase_router)
app.include_router(risk_phase_map_router)
app.include_router(risk_assessment_router)
app.include_router(equipment_router)
app.include_router(phase_task_mapping_router)
app.include_router(project_router)
app.include_router(project_task_router)
app.include_router(project_phase_router)
app.include_router(t_users_router)
app.include_router(project_map_task_router)
app.include_router(project_task_docs)
app.include_router(login_router)
app.include_router(user_role_mapping)
app.include_router(project_comments_router)
app.include_router(incident_report_router)
app.include_router(websocket_router)
app.include_router(roles_screen_router)
app.include_router(action_screen_router)
app.include_router(screens_router)
app.include_router(file_upload_routes)
app.include_router(task_doc_pdf_route)
# app.include_router(auth_router.router)
app.include_router(forgot_password)
app.include_router(change_password_router)
# app.include_router(user_registration)
app.include_router(testing_asset_types_router)
app.include_router(task_work_log_router)
app.include_router(users_router)
app.include_router(project_details_router)
app.include_router(change_request_router)
app.include_router(work_flow_stages_router)
app.include_router(risk_assessment_template_router)
app.include_router(projects_router)
# Instrumentation
Instrumentator().instrument(app).expose(app)
app.include_router(template_type_router)

@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc):
    logger.error(f"HTTPException: {exc.status_code}{exc.detail}")
    return await http_exception_handler(request, exc)

# access images from folder
app.mount("/project_files", StaticFiles(directory="project_files"), name="project_files")
app.mount("/users_profile", StaticFiles(directory="users_profile"), name="users_profile")
app.mount("/change_request_files", StaticFiles(directory="change_request_files"), name="change_request_files")


from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="AI Verify Dev API (JWT Bearer Authentication)",
        routes=app.routes,
    )

    # ✅ Add your server list manually (to restore `/api`)
    openapi_schema["servers"] = [
        {"url": "/api"}
    ]

    # 🔒 Add global JWT Bearer authentication
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token here (e.g. Bearer eyJhbGciOi...)",
        }
    }

    # 👇 Apply security globally
    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

# ✅ Replace FastAPI's default OpenAPI generator
app.openapi = custom_openapi
