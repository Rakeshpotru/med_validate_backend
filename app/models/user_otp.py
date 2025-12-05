from sqlalchemy import (
    Table, Column, Integer, String, Boolean, TIMESTAMP, MetaData, ForeignKey
)
from sqlalchemy.sql import func

metadata = MetaData(schema="uch_dev")



# user_otp = Table(
#     "user_otp",
#     metadata,
#
# Column("user_otp_id", Integer, primary_key=True),
#     Column("user_id", Integer, ForeignKey("ai_verify.users.user_id", ondelete="CASCADE"), nullable=False),
#     Column("otp", String(10), nullable=False),
#     Column("otp_expiry_date", TIMESTAMP, nullable=False),
#     Column("created_date", TIMESTAMP),
#     Column("updated_at",TIMESTAMP),
# )
#
# user_password_history = Table(
#     "user_password_history",
#     metadata,
#     Column("password_history_id", Integer, primary_key=True, autoincrement=True),
#     Column("user_id", Integer, ForeignKey("ai_verify.users.user_id", ondelete="CASCADE"), nullable=False),
#     Column("old_password", String, nullable=False),
#     Column("password_changed_date", TIMESTAMP, server_default=func.current_timestamp()),
# )
