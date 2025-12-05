from sqlalchemy import Table, Column, Integer, ForeignKey, Boolean
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

projects_user_mapping_table = Table(
    "projects_user_mapping",
    metadata,
    Column("project_user_map_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id"))),
    Column("user_id", Integer, ForeignKey(transaction_schema_fk("users.user_id"))),
    Column("is_active", Boolean, default=True),
    schema=transaction_schema,
)
