
from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.db.metadata import metadata
from app.db.database import transaction_schema

user_image_history = Table(
    "user_image_history",
    metadata,
    Column("image_history_id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),

    Column("image_url", String, nullable=False),
    Column("image_changed_date", DateTime(timezone=True), default=datetime.utcnow),
    Column("reason", String(100)),
    schema=transaction_schema,
)
