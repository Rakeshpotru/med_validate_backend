from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

sdlc_phases_table = Table(
    "sdlc_phases",
    metadata,
    Column("phase_id", Integer, primary_key=True, autoincrement=True),
    Column("phase_name", String),
    Column("is_active", Boolean, default=True),
    Column("order_id", Integer),
    Column("phase_code", String),
    schema=master_schema
)

