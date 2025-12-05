# from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime
# from app.db.metadata import metadata
# from app.db.database import transaction_schema
#
# users = Table(
#     "users",
#     metadata,
#     Column("user_id", Integer, primary_key=True, autoincrement=True),
#     Column("user_name", String),
#     Column("email", String),
#     Column("password", String),
#     Column("is_active", Boolean),
#     Column("created_by", Integer),
#     Column("created_date", DateTime(timezone=True)),
#     Column("updated_by", Integer),
#     Column("updated_date", DateTime(timezone=True)),
#
#     schema=transaction_schema,
# )

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime
from app.db.metadata import metadata
from app.db.database import transaction_schema

users = Table(
    "users",
    metadata,
    Column("user_id", Integer, primary_key=True, autoincrement=True),
    Column("user_code", String),
    Column("user_first_name", String),
    Column("user_middle_name", String),
    Column("user_last_name", String),
    Column("user_name", String),
    Column("email", String, unique=True),
    Column("user_phone", String),
    Column("password", String),
    Column("is_temporary_password", Boolean, default=False),
    Column("last_password_changed_date", DateTime(timezone=True)),
    Column("password_validity_date", DateTime(timezone=True)),
    Column("is_active", Boolean, default=True),
    Column("login_failed_count", Integer, default=0),
    Column("is_user_locked", Boolean, default=False),
    Column("user_locked_time", DateTime(timezone=True)),
    Column("user_address", String),
    Column("created_by", Integer),
    Column("created_date", DateTime(timezone=True)),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    Column("image_url", String),
    schema=transaction_schema,
)
