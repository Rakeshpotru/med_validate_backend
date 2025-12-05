from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey ,Boolean
from app.db.metadata import metadata
from app.db.database import transaction_schema, master_schema, master_schema_fk, transaction_schema_fk

projects = Table(
    "projects",
    metadata,
    Column("project_id", Integer, primary_key=True, autoincrement=True),
    Column("project_name", String),
    Column("project_description", String),
    Column("status_id", Integer, ForeignKey(master_schema_fk("status.status_id"))),
    Column("risk_assessment_id", Integer, ForeignKey(master_schema_fk("risk_assessments.risk_assessment_id"))),
    Column("equipment_id", Integer, ForeignKey(master_schema_fk("equipment_list.equipment_id"))),
    Column("created_by", Integer),
    Column("created_date", DateTime(timezone=True)),
    Column("start_date", DateTime(timezone=True)),
    Column("end_date", DateTime(timezone=True)),
    Column("updated_by", Integer),
    Column("updated_date", DateTime(timezone=True)),
    Column("is_active", Boolean, default=True),
    Column("renewal_year", Integer),
    Column("make", String),
    Column("model", Integer),
    Column("json_template_id",Integer,ForeignKey(transaction_schema_fk("json_template_transactions.transaction_template_id"))),
    schema=transaction_schema
)
