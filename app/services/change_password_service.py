
import logging
from fastapi import HTTPException
from app.schemas.change_password_schema import ChangePasswordRequest
from app.db.database import database
from app.db.transaction.users import users as users_table
from app.db.transaction.user_password_history import user_password_history
from datetime import datetime, timezone, timedelta
from app.security import verify_password, get_password_hash
from app.utils.db_transaction import with_transaction
from app.utils.validations import is_password_reused, validate_password

# Use the application logger
logger = logging.getLogger(__name__)

@with_transaction
async def change_user_password(payload: ChangePasswordRequest, current_user: dict):
    """
    Change the user's password with full validation, password reuse prevention,
    and audit logging.
    """

    user_id = current_user["user_id"]

    # logger.info(f"Initiating password change for user_id={user_id}", extra={"email": current_user["email"]})


    try:
        # 1. Fetch current user record
        query = users_table.select().where(users_table.c.user_id == user_id)
        user = await database.fetch_one(query)
        if not user:
            # logger.warning(f"User not found for user_id={user_id}",extra={"email": current_user["email"]})
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Validate old password
        if not verify_password(payload.old_password, user["password"]):
            # logger.warning("Old password mismatch", extra={"email": current_user["email"]})
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        # 3. Validate new password complexity
        if not validate_password(payload.new_password):
            # logger.warning("New password complexity validation failed", extra={"email": current_user["email"]})
            raise HTTPException(
                status_code=400,
                detail=(
                    "Password must be at least 12 characters long, include mixed case, "
                    "a number, and a special character."
                )
            )

        # 4. Check new password and confirm password match
        if payload.new_password != payload.confirm_password:
            # logger.warning("New password and confirmation do not match", extra={"email": current_user["email"]})
            raise HTTPException(status_code=400, detail="New passwords do not match")

        # 5. Check if password is reused
        if await is_password_reused(user_id, payload.new_password):
            # logger.warning("Password reuse attempt detected", extra={"email": current_user["email"]})
            raise HTTPException(status_code=400, detail="Cannot reuse one of the last 5 passwords")

        # 6. Hash new password
        hashed_password = get_password_hash(payload.new_password)
        now = datetime.now(timezone.utc).replace(tzinfo=None)


        # 7. Archive old password to history
        await database.execute(
            user_password_history.insert().values(
                user_id=user_id,
                old_password=user["password"],
                password_changed_date=now
            )
        )

        # 8. Update user password and metadata
        await database.execute(
            users_table.update()
            .where(users_table.c.user_id == user_id)
            .values(
                password=hashed_password,
                is_temporary_password=False,
                last_password_changed_date=now,
                password_validity_date=now + timedelta(days=90),
                updated_date=now
            )
        )

        # logger.info("Password changed successfully", extra={"email": current_user["email"]})
        return {"status_code": 200, "detail": "Password changed successfully"}

    except HTTPException as http_exc:
        # Already handled exception, just re-raise after logging
        # logger.error(f"HTTPException during password change: {http_exc.detail}", extra={"email": current_user["email"]})
        raise http_exc

    except Exception :
        # Log unexpected errors
        logger.exception(f"Unexpected error occurred while changing password for user_id={user_id}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request"
        )
