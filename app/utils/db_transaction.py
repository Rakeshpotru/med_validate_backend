from functools import wraps
from app.db.database import database

def with_transaction(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async with database.transaction():
                return await func(*args, **kwargs)
        except Exception as e:
            # Optional logging here
            print(f"Transaction rolled back due to error: {e}")
            raise
    return wrapper
