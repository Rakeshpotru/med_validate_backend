from sqlalchemy import create_engine
from app.db.metadata import metadata
from app.config import config

# Import all tables (this runs __init__.py inside app.db, registering all tables)
import app.db
# from app.db import database

# Use the same DATABASE_URL from your config
engine = create_engine(config.DATABASE_URL)

def create_all_tables():
    print("Creating tables in PostgreSQL...")
    metadata.create_all(engine)
    print("All tables created successfully.")

if __name__ == "__main__":
    create_all_tables()
