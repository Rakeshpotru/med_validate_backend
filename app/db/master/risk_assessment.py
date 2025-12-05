
from sqlalchemy import Table, Column, Integer, String, Boolean,Text
from app.db.metadata import metadata
from app.db.database import master_schema

risk_assessment_table = Table(
    "risk_assessments",
    metadata,
    Column("risk_assessment_id", Integer, primary_key=True, autoincrement=True),
    Column("risk_assessment_name", String),
    Column("is_active", Boolean, default=True),
    Column("risk_assessment_description", Text),  # New column added here
    schema=master_schema
)
