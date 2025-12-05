from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

project_comments_table = Table(
    "project_comments",
    metadata,
    Column("comment_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id"))),
    Column("project_phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id"))),
    Column("project_task_id", Integer, ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id"))),
    Column("description", String),
    Column("commented_by", Integer),
    Column("comment_date", DateTime(timezone=True)),
    Column("is_resolved", Boolean),
    Column("resolved_by", Integer),  # New column for who resolved the comment
    Column("resolved_date", DateTime(timezone=True)),  # New column for when it was resolved
    Column("updated_by", Integer),
    Column("update_date", DateTime(timezone=True)),
    Column("is_direct_comment", Boolean, default=True),
    schema=transaction_schema,
)
