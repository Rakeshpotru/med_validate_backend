# master tables
from app.db.metadata import metadata
from app.db.master.user_roles import user_roles_table
from app.db.master.status import status_table
from app.db.master.sdlc_tasks import sdlc_tasks_table
from app.db.master.sdlc_phases import sdlc_phases_table
from app.db.master.risk_sdlcphase_mapping import risk_sdlcphase_mapping_table
from app.db.master.equipment_ai_docs import equipment_ai_docs_table
from app.db.master.risk_assessment import risk_assessment_table
from app.db.master.equipment import equipment_list_table
from app.db.master.actions import actions_table
from app.db.master.screens import screens_table
from app.db.master.sdlc_phase_tasks_mapping import sdlc_phase_tasks_mapping_table
from app.db.master.testing_asset_types import testing_asset_types_table
from app.db.master.template_types import template_types_table
from app.db.master.json_templates import json_templates_table
from app.db.master.template_format_types import template_format_types_table

# transaction tables
from app.db.transaction.project_tasks_list import project_tasks_list_table
from app.db.transaction.users import users
from app.db.transaction.project_task_users import project_task_users_table
from app.db.transaction.projects import projects
from app.db.transaction.project_comments import project_comments_table
from app.db.transaction.project_phase_users import project_phase_users_table
from app.db.transaction.comment_replies import comment_replies_table
from app.db.transaction.project_files import project_files_table
from app.db.transaction.projects_user_mapping import projects_user_mapping_table
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.transaction.project_phases_list import project_phases_list_table
from app.db.transaction.change_request import change_request_table
from app.db.transaction.incident_reports import incident_report_table
from app.db.transaction.task_work_log import task_work_log_table
from app.db.transaction.change_request_user_mapping import change_request_user_mapping_table
from app.db.transaction.json_template_transactions import json_template_transactions

# docs tables
from app.db.docs.task_docs import task_docs_table

# security tables
from app.db.security.screen_action_mapping import screen_action_mapping_table
from app.db.security.screen_action_mapping_roles import screen_action_mapping_roles_table