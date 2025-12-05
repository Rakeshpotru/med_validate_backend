from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

project_task_users_table = Table(
    "project_task_users",
    metadata,
    Column("project_task_user_map_id", Integer, primary_key=True, autoincrement=True),
    Column("project_task_id", Integer, ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id"))),
    Column("user_id", Integer, ForeignKey(transaction_schema_fk("users.user_id"))),
    Column("user_is_active", Boolean),
    Column("to_user_id", Integer),
    Column("user_transfer_reason", String),
    Column("submitted", Boolean, nullable=False, server_default="false"),
    schema=transaction_schema,
)
