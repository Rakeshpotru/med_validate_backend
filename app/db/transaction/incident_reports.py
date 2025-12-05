from sqlalchemy import Boolean, Table, Column, Integer, String, DateTime, ForeignKey, Text
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

incident_report_table = Table(
    "incident_reports",
    metadata,
    Column("incident_report_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id")), nullable=True),
    Column("phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id")), nullable=True),
    Column("task_id", Integer, ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id")), nullable=True),
    Column("test_script_name", String, nullable=True),
    Column("testcase_number", String, nullable=True),
    Column("failure_type", Integer, nullable=True),
    Column("assigned_to", Integer, ForeignKey(transaction_schema_fk("users.user_id")), nullable=True),
    Column("document", Text, nullable=True),
    Column("raise_comment", String, nullable=True),
    Column("raised_by", Integer, ForeignKey(transaction_schema_fk("users.user_id")), nullable=True),
    Column("raised_date", DateTime, nullable=True),  # Use DateTime if SQL changes to TIMESTAMP
    Column("resolved_by", Integer, ForeignKey(transaction_schema_fk("users.user_id")), nullable=True),
    Column("resolved_date", DateTime, nullable=True),
    Column("resolve_comment", String, nullable=True),
    Column("is_resolved", Boolean, default=False, nullable=False),
    schema=transaction_schema,
)

incident_reports_table = Table(
    "incident_report",
    metadata,
    Column("incident_report_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id")), nullable=True),
    Column("phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id")), nullable=True),
    Column("task_id", Integer, ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id")), nullable=True),
    Column("raised_by", Integer, ForeignKey(transaction_schema_fk("users.user_id")), nullable=True),
    Column("raised_date", DateTime, nullable=True),  # Use DateTime if SQL changes to TIMESTAMP
    Column("is_resolved", Boolean, default=False, nullable=False),
    schema=transaction_schema,
)

incident_report_transactions = Table(
    "incident_report_transactions",
    metadata,
    Column("incident_report_transaction_id", Integer, primary_key=True, autoincrement=True),
    Column("incident_report_id", Integer),
    Column("transaction_template_id", Integer),
    Column("role_id", Integer),
    Column("status", Integer),
    Column("created_date", DateTime, nullable=True),
    schema=transaction_schema,
)