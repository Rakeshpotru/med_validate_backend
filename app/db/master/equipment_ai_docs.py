from sqlalchemy import Table, Column, Integer, ForeignKey,String
from sqlalchemy.dialects import postgresql
from app.db.metadata import metadata
from app.db.database import master_schema, master_schema_fk


equipment_ai_docs_table = Table(
    "equipment_ai_docs",
    metadata,
    Column("equipment_doc_id", Integer, primary_key=True, autoincrement=True),
    Column("equipment_id", Integer, ForeignKey(master_schema_fk("equipment_list.equipment_id"))),
    Column("phase_id", Integer, ForeignKey(master_schema_fk("sdlc_phases.phase_id"))),
    Column("document_json", String),
    schema=master_schema
)