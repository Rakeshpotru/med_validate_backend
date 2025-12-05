from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, func
from app.db.metadata import metadata
from app.db.database import transaction_schema

user_password_history = Table(
    "user_password_history",
    metadata,
    Column("password_history_id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
    Column("old_password", String, nullable=False),
    Column("password_changed_date", DateTime(timezone=True), server_default=func.now(), nullable=False),
    schema=transaction_schema,
)
