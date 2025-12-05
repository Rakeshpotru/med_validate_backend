from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk

equipment_list_table = Table(
    "equipment_list",
    metadata,
    Column("equipment_id", Integer, primary_key=True, autoincrement=True),
    Column("equipment_name", String),
    Column("is_ai_verified", Boolean),
    Column("created_by", Integer),
    Column("created_date", DateTime(timezone=True)),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    Column("equipment_code", String),
    Column("is_active", Boolean, default=True),
    # Foreign Key using master_schema_fk helper
    Column("asset_type_id", Integer, ForeignKey(master_schema_fk("testing_asset_types.asset_id")), nullable=True),
    schema=master_schema
)
