from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

change_request_user_mapping_table = Table(
    "change_request_user_mapping",
    metadata,
    Column("change_request_user_mapping_id", Integer, primary_key=True, autoincrement=True),
    Column("change_request_id", Integer, ForeignKey(transaction_schema_fk("change_request.change_request_id")), nullable=False),
    Column("verified_by", Integer, ForeignKey(transaction_schema_fk("users.user_id")), nullable=True),
    Column("verified_date", DateTime, nullable=True),
    Column("is_verified", Boolean, default=None, nullable=True),
    Column("reject_reason", Text, nullable=True),
    Column("user_is_active", Boolean, default=True, nullable=False),
    schema=transaction_schema,
)
