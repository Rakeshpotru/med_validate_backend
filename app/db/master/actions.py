from sqlalchemy import Table, Column, Integer, String, Boolean, TIMESTAMP
from app.db.metadata import metadata
from app.db.database import master_schema

actions_table = Table(
    "actions",
    metadata,
    Column("action_id", Integer, primary_key=True, autoincrement=True),
    Column("action_name", String, nullable=False),
    Column("is_active", Boolean, default=True),
    Column("created_by", Integer, nullable=False),
    Column("created_date", TIMESTAMP, server_default="NOW()"),
    Column("updated_by", Integer),
    Column("updated_date", TIMESTAMP),
    schema=master_schema
)
