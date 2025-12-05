from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

work_flow_stages_table = Table(
    "work_flow_stages",
    metadata,
    Column("work_flow_stage_id", Integer, primary_key=True, autoincrement=True),
    Column("work_flow_stage_name", String),
    Column("is_active", Boolean),  # note: matches your DB field spelling
    schema=master_schema
)
