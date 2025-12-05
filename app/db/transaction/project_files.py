from sqlalchemy import Table, Column, Integer, String, ForeignKey, Boolean
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

project_files_table = Table(
    "project_files",
    metadata,
    Column("project_file_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id"))),
    Column("file_name", String),
    Column("is_active", Boolean, default=True),
    schema=transaction_schema,
)
