from sqlalchemy import Table, Column, Integer, ForeignKey,Boolean
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk


sdlc_phase_tasks_mapping_table = Table(
    "sdlc_phase_tasks_mapping",
    metadata,
    Column("phase_task_map_id", Integer, primary_key=True, autoincrement=True),
    Column("phase_id", Integer, ForeignKey(master_schema_fk("sdlc_phases.phase_id"))),
    Column("task_id", Integer, ForeignKey(master_schema_fk("sdlc_tasks.task_id"))),
    Column("is_active", Boolean, default=True),
    schema=master_schema
)