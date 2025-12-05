import databases
import sqlalchemy
from app.db.metadata import metadata
from app.config import config

# Detect if using SQLite (no schema support)
IS_SQLITE = "sqlite" in config.DATABASE_URL


master_schema = "ai_verify_master" if not IS_SQLITE else None
transaction_schema = "ai_verify_transaction" if not IS_SQLITE else None
docs_schema = "ai_verify_docs" if not IS_SQLITE else None
security_schema = "ai_verify_security" if not IS_SQLITE else None  # <-- Added security schema
configuration_schema = "ai_verify_configuration" if not IS_SQLITE else None  # <-- Added security schema


def master_schema_fk(ref: str) -> str:
    return f"{master_schema + '.' if master_schema else ''}{ref}"

def transaction_schema_fk(ref: str) -> str:
    return f"{transaction_schema + '.' if transaction_schema else ''}{ref}"

def docs_schema_fk(ref: str) -> str:
    return f"{docs_schema + '.' if docs_schema else ''}{ref}"


def security_schema_fk(ref: str) -> str:
    return f"{security_schema + '.' if security_schema else ''}{ref}"


def configuration_schema_fk(ref: str) -> str:
    return f"{configuration_schema + '.' if configuration_schema else ''}{ref}"

# Create engine
connect_args = {"check_same_thread": False} if IS_SQLITE else {}
engine = sqlalchemy.create_engine(config.DATABASE_URL, connect_args=connect_args)

# Create all tables
metadata.create_all(engine)

# Set up the database object
database = databases.Database(
    config.DATABASE_URL, force_rollback=config.DB_FORCE_ROLL_BACK
)

