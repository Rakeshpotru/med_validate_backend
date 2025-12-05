# from sqlalchemy import Table, Column, Integer, String, JSON, TIMESTAMP, text,ForeignKey
# from app.db.metadata import metadata
# from app.db.database import master_schema_fk,master_schema
#
#
# risk_assessment_template_table = Table(
#     "risk_assessment_template",
#     metadata,
#     Column("risk_assessment_template_id", Integer, primary_key=True, autoincrement=True),
#     Column("risk_assessment_template_name", String(255), nullable=False),
#     Column("risk_assessment_template_json", JSON, nullable=False),
#     Column("template_version", Integer, nullable=False, server_default=text("1")),
#     Column("asset_type_id", Integer, ForeignKey(master_schema_fk("testing_asset_types.asset_id")), nullable=True),
#
#     Column("created_date", TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")),
#     schema=master_schema
# )
