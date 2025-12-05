from sqlalchemy import Table, Column, Integer, Boolean
from app.db.metadata import metadata
from app.db.database import security_schema

screen_action_mapping_table = Table(
    "screen_action_mapping",
    metadata,
    Column("screen_action_id", Integer, primary_key=True, autoincrement=True),
    Column("screen_id", Integer, nullable=False),
    Column("action_id", Integer, nullable=False),
    Column("is_active", Boolean, default=True),
    schema=security_schema
)
