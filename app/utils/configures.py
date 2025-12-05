from app.db.database import database
from app.db.configuration.configurations import configurations as configurations_table

async def get_config_value(key: str, default=None, value_type=int):
    """
    Fetch a configuration value from the database.
    Converts it to `value_type` if possible, otherwise returns default.
    """
    query = configurations_table.select().where(
        configurations_table.c.config_key == key,
        configurations_table.c.is_active == True
    )
    result = await database.fetch_one(query)
    if result:
        try:
            return value_type(result["config_value"])
        except (ValueError, TypeError):
            return default
    return default
