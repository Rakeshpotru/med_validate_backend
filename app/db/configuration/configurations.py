from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, Text, func
from app.db.metadata import metadata
from app.db.database import configuration_schema

configurations = Table(
    "configurations",
    metadata,
    Column("config_id", Integer, primary_key=True, autoincrement=True),
    Column("config_key", String(100), unique=True, nullable=False),
    Column("config_value", Text, nullable=False),
    Column("description", Text),
    Column("is_active", Boolean, default=True),
    Column("created_by", Integer),
    Column("created_date", DateTime(timezone=True), server_default=func.now()),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True), nullable=True),

    schema=configuration_schema,
)
