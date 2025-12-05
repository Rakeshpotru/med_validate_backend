from sqlalchemy import Table, Column, Integer, ForeignKey, JSON, DateTime, func
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk  # "ai_verify_transaction"

json_template_transactions = Table(
    "json_template_transactions",
    metadata,
    Column("transaction_template_id", Integer, primary_key=True, autoincrement=True),
    Column("template_json", JSON, nullable=False),
    Column("created_by", Integer),
    Column("created_date", DateTime, server_default=func.now()),
    schema=transaction_schema,
)
