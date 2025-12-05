from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey, func
from app.db.metadata import metadata
from app.db.database import transaction_schema

user_otp = Table(
    "user_otp",
    metadata,
    Column("user_otp_id", Integer, primary_key=True, autoincrement=True),
    Column(
        "user_id",
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),  # schema removed here
        nullable=False,
    ),
    Column("otp", String(10), nullable=False),
    Column("otp_expiry_date", DateTime(timezone=True), nullable=False),
    Column("created_date", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), onupdate=func.now()),
    schema=transaction_schema,  # optional, can be None
)

