import logging
from fastapi import HTTPException
from app.db import user_role_mapping_table, user_roles_table
from app.db.database import database

from app.db.transaction.user_audit import user_audit

from app.db.transaction.users import users as users_table
from sqlalchemy import select, insert
from datetime import datetime,timezone
from app.config import config

# from app.models.users import
naive_utc_time = datetime.now(timezone.utc).replace(tzinfo=None)


logger = logging.getLogger(__name__)


async def fetch_user_by_email(email: str):
    logger.debug(f"Fetching user by email: {email}")
    query = users_table.select().where(
        (users_table.c.email == email) & (users_table.c.is_active == True)
    )
    user = await database.fetch_one(query)
    if user:
        logger.info(f"User found: {email}")
        logger.info(f"User found 2: id={user['user_id']}, name={user['user_name']}")

    else:
        logger.warning(f"No active user found with email: {email}")
    return user



# ------------------------
# Role Handling Function
# ------------------------

async def get_user_role(user_id: int) -> dict | None:
    """
    Fetch the first role assigned to a user.
    Returns dict {"role_id": id, "role_name": name} if found, else None.
    """
    role_query = (
        select(user_roles_table.c.role_id, user_roles_table.c.role_name)
        .select_from(
            user_role_mapping_table.join(
                user_roles_table,
                user_role_mapping_table.c.role_id == user_roles_table.c.role_id
            )
        )
        .where(user_role_mapping_table.c.user_id == user_id)
        .limit(1)
    )
    role = await database.fetch_one(role_query)
    if role:
        return {"id": role["role_id"], "name": role["role_name"]}
    return None



async def get_or_assign_role(user_id: int):
    """
    Fetch user role or assign default if none exists.
    """
    try:
        role_query = (
            select(user_roles_table.c.role_id, user_roles_table.c.role_name)
            .select_from(
                user_role_mapping_table.join(
                    user_roles_table,
                    user_role_mapping_table.c.role_id == user_roles_table.c.role_id
                )
            )
            .where(user_role_mapping_table.c.user_id == user_id)
            .limit(1)
        )
        role = await database.fetch_one(role_query)

        if not role:
            logger.info(f"No role found for user {user_id}. Assigning default role.")
            await database.execute(
                insert(user_role_mapping_table).values(user_id=user_id, role_id=config.DEFAULT_ROLE_ID)
            )
            # Re-fetch the role after assignment
            role = await database.fetch_one(role_query)

        return role

    except Exception as e:
        logger.error(f"Error in _get_or_assign_role: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def reset_user_login_state(user_id: int):
    """
    Reset login failed count and unlock the user.
    """
    logger.info(f"Resetting login state for user: {user_id}")
    await database.execute(
        users_table.update()
        .where(users_table.c.user_id == user_id)
        .values(
            login_failed_count=0,
            is_user_locked=False,
            user_locked_time=None
        )
    )


async def log_user_audit(user_id: int | None, action: str, status: str):
    """
    Log user login/logout actions.
    """
    logger.info(f"Logging audit: user_id={user_id}, action={action}, status={status}")
    await database.execute(
        user_audit.insert().values(
            user_id=user_id,
            action=action,
            status=status,
            timestamp=naive_utc_time
        )
    )