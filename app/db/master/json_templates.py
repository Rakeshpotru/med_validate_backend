from sqlalchemy import Table, Column, Integer, String, JSON, Float, TIMESTAMP, ForeignKey, text
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk

json_templates_table = Table(
    "json_templates",
    metadata,
    Column("template_id", Integer, primary_key=True, autoincrement=True),
    Column("template_name", String(255), nullable=False),
    Column("template_type_id", Integer, ForeignKey(master_schema_fk("template_types.template_type_id")), nullable=False),
    Column("json_template", JSON, nullable=False),
    Column("created_by", Integer, nullable=False),
    Column("created_date", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")),
    Column("template_version", Float, nullable=False, server_default=text("1")),
    schema=master_schema
)















































































































