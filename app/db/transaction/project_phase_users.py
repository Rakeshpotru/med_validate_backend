from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

project_phase_users_table = Table(
    "project_phase_users",
    metadata,
    Column("project_phase_user_map_id", Integer, primary_key=True, autoincrement=True),
    Column("project_phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id"))),
    Column("user_id", Integer, ForeignKey(transaction_schema_fk("users.user_id"))),
    Column("user_is_active", Boolean),
    Column("to_user_id", Integer),
    Column("user_transfer_reason", String),
    schema=transaction_schema,
)
