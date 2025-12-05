from sqlalchemy import Table, Column, Integer, ForeignKey, Boolean
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk


risk_sdlcphase_mapping_table = Table(
    "risk_sdlcphase_mapping",
    metadata,
    Column("risk_phase_map_id", Integer, primary_key=True, autoincrement=True),
    Column("risk_assessment_id", Integer, ForeignKey(master_schema_fk("risk_assessments.risk_assessment_id"))),
    Column("phase_id", Integer, ForeignKey(master_schema_fk("sdlc_phases.phase_id"))),
    Column("is_active", Boolean, default=True),
    schema=master_schema
)