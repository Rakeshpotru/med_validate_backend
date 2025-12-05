from sqlalchemy import Table, Column, Integer, Boolean, TIMESTAMP
from app.db.metadata import metadata
from app.db.database import security_schema

screen_action_mapping_roles_table = Table(
    "screen_action_mapping_roles",
    metadata,
    Column("screen_action_mapping_role_id", Integer, primary_key=True, autoincrement=True),
    Column("screen_action_id", Integer, nullable=False),
    Column("role_id", Integer, nullable=False),
    Column("created_date", TIMESTAMP, server_default="NOW()"),
    Column("created_by", Integer, nullable=False),
    Column("updated_date", TIMESTAMP),
    Column("updated_by", Integer),
    Column("is_active", Boolean, default=True),
    schema=security_schema
)
