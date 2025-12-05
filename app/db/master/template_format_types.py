from sqlalchemy import Table, Column, Integer, String, Boolean, text
from app.db.metadata import metadata
from app.db.database import master_schema

template_format_types_table = Table(
    "template_format_types",
    metadata,
    Column("template_format_type_id", Integer, primary_key=True, autoincrement=True),
    Column("format_name", String(255), nullable=False),
    Column("section", Boolean, server_default=text("true")),
    Column("weightage", Boolean, server_default=text("true")),
    Column("table", Boolean, server_default=text("true")),  # Note: 'table' is a reserved keyword; ensure quoting if needed in queries
    schema=master_schema
)