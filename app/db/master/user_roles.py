from sqlalchemy import Table, Column, Integer, String, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema

user_roles_table = Table(
    "user_roles",
    metadata,
    Column("role_id", Integer, primary_key=True, autoincrement=True),
    Column("role_name", String),
    Column("is_active", Boolean, default=True),
    schema=master_schema
)

