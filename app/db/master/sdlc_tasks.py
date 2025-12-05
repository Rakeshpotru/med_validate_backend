from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

sdlc_tasks_table = Table(
    "sdlc_tasks",
    metadata,
    Column("task_id", Integer, primary_key=True, autoincrement=True),
    Column("task_name", String),
    Column("is_active", Boolean, default=True),
    Column("order_id", Integer),
    Column("task_description", String),
    schema=master_schema
)

