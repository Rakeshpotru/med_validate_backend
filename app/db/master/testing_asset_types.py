from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

testing_asset_types_table = Table(
    "testing_asset_types",
    metadata,
    Column("asset_id", Integer, primary_key=True, autoincrement=True),
    Column("asset_name", String(255), nullable=False),
    Column("is_active", Boolean, default=True),
    schema=master_schema
)
