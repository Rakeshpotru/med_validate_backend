from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

status_table = Table(
    "status",
    metadata,
    Column("status_id", Integer, primary_key=True, autoincrement=True),
    Column("status_name", String),
    Column("is_active", Boolean, default=True),
    schema=master_schema
)

