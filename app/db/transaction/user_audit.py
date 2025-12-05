from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, Boolean
from app.db.metadata import metadata
from app.db.database import transaction_schema

user_audit = Table(
    "user_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.user_id", ondelete="SET NULL"),  # remove schema prefix
        nullable=True,
    ),
    Column("action", String(20), nullable=False),
    Column("status", String(10), nullable=False),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    schema=transaction_schema,  # optional, can be None
)

