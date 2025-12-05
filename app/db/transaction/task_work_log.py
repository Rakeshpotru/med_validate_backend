from sqlalchemy import Table, Column, Integer, String, ForeignKey, DateTime, func
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

task_work_log_table = Table(
    "task_work_log",
    metadata,
    Column("task_work_log_id", Integer, primary_key=True, autoincrement=True),
    Column( "project_task_id",Integer,ForeignKey(transaction_schema_fk("project_tasks_list.project_task_id"), ondelete="CASCADE"),nullable=False,),
    Column("user_id",Integer,ForeignKey(transaction_schema_fk("users.user_id"), ondelete="SET NULL"),nullable=False,),
    Column("remarks", String, nullable=True),
    Column("created_date",DateTime(timezone=True),server_default=func.now(),nullable=False,),
    schema=transaction_schema,
)
