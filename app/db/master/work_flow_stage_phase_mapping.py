from sqlalchemy import Table, Column, Integer, Boolean, ForeignKey, DateTime
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk

work_flow_stage_phase_mapping_table = Table(
    "work_flow_stage_phase_mapping",
    metadata,
    Column("work_flow_stage_phase_mapping_id", Integer, primary_key=True, autoincrement=True),
    Column("work_flow_stage_id", Integer, ForeignKey(master_schema_fk("work_flow_stages.work_flow_stage_id"))),
    Column("sdlc_phase_id", Integer, ForeignKey(master_schema_fk("sdlc_phases.phase_id"))),
    Column("is_active", Boolean, default=True),
    Column("created_by", Integer),
    Column("created_date", DateTime),
    Column("updated_by", Integer),
    Column("updated_date", DateTime),
    schema=master_schema
)
