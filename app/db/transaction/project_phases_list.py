from sqlalchemy import Table, Column, Integer, ForeignKey,Boolean, DateTime
from app.db.metadata import metadata
from app.db.database import transaction_schema, master_schema, transaction_schema_fk, master_schema_fk

project_phases_list_table = Table(
    "project_phases_list",
    metadata,
    Column("project_phase_id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id"))),
    Column("phase_id", Integer, ForeignKey(master_schema_fk("sdlc_phases.phase_id"))),
    Column("phase_order_id", Integer),
    Column("status_id", Integer, ForeignKey(master_schema_fk("status.status_id"))),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    schema=transaction_schema,
)
