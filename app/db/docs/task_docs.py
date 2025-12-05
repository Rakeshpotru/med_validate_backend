from sqlalchemy import Table, Column, Integer, Text, Boolean, ForeignKey, DateTime,Numeric
from app.db.metadata import metadata
from app.db.database import docs_schema, transaction_schema_fk

task_docs_table = Table(
    "task_docs",
    metadata,
    Column("task_doc_id", Integer, primary_key=True, autoincrement=True),
    Column("project_task_id",Integer,ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id"))),
    Column("document_json", Text),
    Column("is_latest", Boolean),
    Column("created_by", Integer),
    Column("created_date", DateTime(timezone=True)),
    Column("doc_version", Numeric(10, 2)),
    Column("project_id", Integer, ForeignKey(transaction_schema_fk("projects.project_id"))),
    Column("project_phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id"))),
    Column("submitted_by", Integer),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    schema=docs_schema,
)
