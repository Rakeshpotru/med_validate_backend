import datetime
import sqlalchemy

metadata = sqlalchemy.MetaData()

from datetime import datetime, UTC


# Reusable helper
def get_utc_now():
    return datetime.now(UTC)



# users_table = Table(
#     "users",
#     metadata,
#     Column("user_id", Integer, primary_key=True, autoincrement=True),
#     Column("user_code", String),
#     Column("user_first_name", String),
#     Column("user_middle_name", String),
#     Column("user_last_name", String),
#     Column("user_email", String, unique=True),
#     Column("user_phone", String),
#     Column("user_password", String),
#     Column("is_temporary_password", Boolean),
#     Column("last_password_changed_date", DateTime),
#     Column("password_validity_date", DateTime),
#     Column("is_active", Boolean, default=True),
#     Column("login_failed_count", Integer, default=0),
#     Column("is_user_locked", Boolean, default=False),
#     Column("user_locked_time", DateTime),
#     Column("created_by", Integer),  # FIXED to Integer
#     Column("created_date", DateTime),
#     Column("updated_by", Integer),
#     Column("updated_date", DateTime),
#     Column("user_address", String),
#     # schema="uch_dev"
# )

# user_audit = sqlalchemy.Table(
#     "user_audit",
#     metadata,
#     sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, index=True),
#     Column("user_id", Integer, ForeignKey("uch_dev.users.user_id", ondelete="SET NULL"), nullable=True),
#     sqlalchemy.Column("action", sqlalchemy.String(20)),
#     sqlalchemy.Column("status", sqlalchemy.String(10)),
#     sqlalchemy.Column("timestamp", sqlalchemy.DateTime(timezone=False)),  # You will insert this using get_utc_now()
#     schema="uch_dev"
# )
#
#
# user_role_map_table = Table(
#     "user_role_mapping",
#     metadata,
#     Column("user_role_map_id", Integer, primary_key=True, autoincrement=True),
#     Column("user_id", Integer),   # FIXED to Integer
#     Column("role_id", Integer),   # FIXED to Integer
#     Column("is_active", Boolean, default=True),
#     Column("created_by", Integer),
#     schema="uch_dev"
# )
