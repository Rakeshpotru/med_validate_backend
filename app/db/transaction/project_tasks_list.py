from sqlalchemy import Table, Column, Integer, ForeignKey,DateTime,func
from app.db.metadata import metadata
from app.db.database import transaction_schema, master_schema, master_schema_fk, transaction_schema_fk

project_tasks_list_table = Table(
    "project_tasks_list",
    metadata,
    Column("project_task_id", Integer, primary_key=True, autoincrement=True),
    Column("project_phase_id", Integer, ForeignKey(transaction_schema_fk("project_phases_list.project_phase_id"))),
    Column("task_id", Integer, ForeignKey(master_schema_fk("sdlc_tasks.task_id"))),
    Column("task_order_id", Integer),
    Column("task_status_id", Integer, ForeignKey(master_schema_fk("status.status_id"))),
    Column("task_users_count", Integer),       # new column
    Column("task_users_submitted", Integer),  #new column
    Column("created_date", DateTime(timezone=True)), #new column
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    Column("task_start_date", DateTime(timezone=True)),
    Column("task_end_date", DateTime(timezone=True)),
    schema=transaction_schema,
)
