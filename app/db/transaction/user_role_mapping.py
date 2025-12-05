from sqlalchemy import Table, Column, Integer, ForeignKey,Boolean
from app.db.metadata import metadata
from app.db.database import transaction_schema, master_schema, transaction_schema_fk, master_schema_fk

user_role_mapping_table = Table(
    "user_role_mapping",
    metadata,
    Column("user_role_map_id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey(transaction_schema_fk("users.user_id"))),
    Column("role_id", Integer, ForeignKey(master_schema_fk("user_roles.role_id"))),
    Column("is_active", Boolean, nullable=False, server_default="true"),
    schema=transaction_schema,
)
