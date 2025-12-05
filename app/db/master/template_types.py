from sqlalchemy import Table, Column, Integer, String, Boolean, text,ForeignKey
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk

template_types_table = Table(
    "template_types",
    metadata,
    Column("template_type_id", Integer, primary_key=True, autoincrement=True),
    Column("template_type_name", String(255), nullable=False),
    Column("is_active", Boolean, nullable=False, server_default=text("true")),
    Column("template_format_type_id", Integer, ForeignKey(master_schema_fk("template_format_types.template_format_type_id")), nullable=False),
    schema=master_schema
)
