from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

change_request_table = Table(
    "change_request",
    metadata,
    Column("change_request_id", Integer, primary_key=True, autoincrement=True),
    Column("change_request_code", String, nullable=False),
    Column("change_request_file", String, nullable=True),
    Column("project_id",Integer,ForeignKey(transaction_schema_fk("projects.project_id")),nullable=False,),
    Column("is_verified", Boolean, nullable=True),
    Column("transaction_template_id",Integer,ForeignKey(transaction_schema_fk("json_template_transactions.transaction_template_id")),nullable=True,),
    schema=transaction_schema,
)









































# change_request_table = Table(
#     "change_request",
#     metadata,
#     Column("change_request_id", Integer, primary_key=True, autoincrement=True),
#     Column("change_request_code", String, nullable=False),
#     Column("change_request_file", String, nullable=True),
#     Column("project_id",Integer,ForeignKey(transaction_schema_fk("projects.project_id")),nullable=False,),
#     Column("verified_by",Integer,ForeignKey(transaction_schema_fk("users.user_id")),nullable=True,),
#     Column("verified_date", DateTime(timezone=True), nullable=True),
#     Column("is_verified", Boolean, nullable=True),
#     Column("reject_reason", String),
#     Column("transaction_template_id",Integer,ForeignKey(transaction_schema_fk("json_template_transactions.transaction_template_id")),nullable=True,),
#     schema=transaction_schema,
# )
