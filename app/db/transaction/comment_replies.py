from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from app.db.metadata import metadata
from app.db.database import transaction_schema, transaction_schema_fk

comment_replies_table = Table(
    "comment_replies",
    metadata,
    Column("reply_id", Integer, primary_key=True, autoincrement=True),
    Column("comment_id", Integer, ForeignKey(transaction_schema_fk("project_comments.comment_id"))),
    Column("reply_description", String),
    Column("replied_by", Integer),
    Column("replied_date", DateTime(timezone=True)),
    Column("updated_by", Integer),
    Column("update_date", DateTime(timezone=True)),
    schema=transaction_schema,
)
