import asyncio
import logging
from datetime import datetime, timedelta, timezone
from fastapi import status
from starlette.responses import JSONResponse

from app.db.database import database
from app.schemas.login_schema import LoginResponse, AuditAction, AuditStatus, LoginRequest
from app.utils.configures import get_config_value
from app.utils.user_utils import (
    fetch_user_by_email,
    reset_user_login_state,
    log_user_audit,
    get_user_role,
)
from app.security import create_access_token, verify_password
from app.db.transaction.users import users as users_table

logger = logging.getLogger(__name__)

# In-memory cache for config values
CONFIG_CACHE = {}
CONFIG_TTL_SECONDS = 60  # refresh every 60s


async def get_cached_config(key: str, type_func=int):
    """Fetch configuration with caching and timestamp TTL."""
    now = datetime.now().timestamp()
    cached = CONFIG_CACHE.get(key)
    if cached and now - cached["ts"] < CONFIG_TTL_SECONDS:
        return cached["val"]

    value = await get_config_value(key, type_func)
    CONFIG_CACHE[key] = {"val": value, "ts": now}
    logger.debug(f"Config cache refreshed for {key}={value}")
    return value


async def check_password_expiry_flag(password_validity_date: datetime | None) -> bool:
    """Check if password expired using cached config."""
    try:
        if not password_validity_date:
            return False

        PASSWORD_EXPIRY_DAYS = await get_cached_config("PASSWORD_EXPIRY_DAYS", int)
        now_utc = datetime.now(timezone.utc)
        if password_validity_date.tzinfo is None:
            password_validity_date = password_validity_date.replace(tzinfo=timezone.utc)

        expired = (now_utc - password_validity_date).days >= PASSWORD_EXPIRY_DAYS
        logger.debug(
            f"Password expiry check: expired={expired}, days={(now_utc - password_validity_date).days}"
        )
        return expired
    except Exception:
        logger.exception("Error while checking password expiry flag")
        return False


async def simple_login(login: LoginRequest):
    """
    Authenticate user with maximum speed.
    - Full logging preserved.
    - Parallel I/O (configs, DB, token).
    - Cached configs.
    - Non-blocking audit logs.
    """
    now = datetime.now(timezone.utc)
    email = login.user_email
    logger.info("Login attempt started", extra={"email": email})

    try:
        # Fetch configuration and user data concurrently
        max_failed_task = asyncio.create_task(get_cached_config("MAX_FAILED_ATTEMPTS", int))
        lock_minutes_task = asyncio.create_task(get_cached_config("LOCK_DURATION_MINUTES", int))
        user_task = asyncio.create_task(fetch_user_by_email(email))

        MAX_FAILED_ATTEMPTS, LOCK_DURATION_MINUTES, user_record = await asyncio.gather(
            max_failed_task, lock_minutes_task, user_task
        )
        logger.debug(
            f"Configs loaded: MAX_FAILED_ATTEMPTS={MAX_FAILED_ATTEMPTS}, "
            f"LOCK_DURATION_MINUTES={LOCK_DURATION_MINUTES}"
        )

        # --- User not found ---
        if not user_record:
            logger.warning("User not found during login", extra={"email": email})
            asyncio.create_task(log_user_audit(None, AuditAction.login, AuditStatus.failure))
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=LoginResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="Invalid credentials",
                ).model_dump(),
            )

        user = dict(user_record._mapping)
        user_id = user["user_id"]
        user_name = user.get("user_name")
        logger.info("User record fetched", extra={"user_id": user_id, "user_name": user_name})

    except Exception:
        logger.exception("Error fetching configuration or user")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error"},
        )

    try:
        failed_attempts = user.get("login_failed_count") or 0
        is_locked = user.get("is_user_locked", False)
        locked_time = user.get("user_locked_time")
        temporary_password = user.get("is_temporary_password")

        # --- Case 1: Account locked ---
        if is_locked and locked_time and now < locked_time:
            remaining = int((locked_time - now).total_seconds() // 60)
            logger.warning(
                "Login blocked - account locked",
                extra={"user_id": user_id, "remaining_minutes": remaining},
            )
            asyncio.create_task(log_user_audit(user_id, AuditAction.login, AuditStatus.failure))
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=LoginResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message=f"Account temporarily locked. Try again after {remaining} minutes.",
                ).model_dump(),
            )

        # --- Case 2: Invalid password ---
        if not verify_password(login.user_password, user["password"]):
            logger.warning(
                "Invalid password attempt",
                extra={"user_id": user_id, "failed_attempts": failed_attempts},
            )

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                # Lock account
                await database.execute(
                    users_table.update()
                    .where(users_table.c.user_id == user_id)
                    .values(user_locked_time=now + timedelta(minutes=LOCK_DURATION_MINUTES))
                )
                logger.error(
                    "Account locked due to repeated failures",
                    extra={"user_id": user_id, "lock_minutes": LOCK_DURATION_MINUTES},
                )
                asyncio.create_task(log_user_audit(user_id, AuditAction.login, AuditStatus.failure))
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content=LoginResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        message="Account locked due to multiple failed login attempts",
                    ).model_dump(),
                )
            else:
                # Increment failure count
                failed_attempts += 1
                lock_required = failed_attempts >= MAX_FAILED_ATTEMPTS
                lock_time = now + timedelta(minutes=LOCK_DURATION_MINUTES) if lock_required else None

                await database.execute(
                    users_table.update()
                    .where(users_table.c.user_id == user_id)
                    .values(
                        login_failed_count=failed_attempts,
                        is_user_locked=lock_required,
                        user_locked_time=lock_time,
                    )
                )

                asyncio.create_task(log_user_audit(user_id, AuditAction.login, AuditStatus.failure))
                remaining = max(0, MAX_FAILED_ATTEMPTS - failed_attempts)
                logger.info(
                    "Invalid credentials; remaining attempts",
                    extra={"user_id": user_id, "remaining": remaining},
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content=LoginResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        message="Invalid credentials",
                        remaining_attempts=remaining,
                    ).model_dump(),
                )

        # --- Case 3: Valid password ---
        logger.info("Password verified", extra={"user_id": user_id})

        # Run slow I/O in parallel
        expiry_task = asyncio.create_task(check_password_expiry_flag(user.get("password_validity_date")))
        reset_task = asyncio.create_task(reset_user_login_state(user_id))
        role_task = asyncio.create_task(get_user_role(user_id))
        token_task = asyncio.create_task(create_access_token(user))

        password_expired, _, role, token = await asyncio.gather(
            expiry_task, reset_task, role_task, token_task
        )

        asyncio.create_task(log_user_audit(user_id, AuditAction.login, AuditStatus.success))
        user_role_name = role["name"] if role else None

        logger.info(
            "Login successful",
            extra={
                "user_id": user_id,
                "user_name": user_name,
                "role": user_role_name,
                "password_expired": password_expired,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=LoginResponse(
                status_code=status.HTTP_200_OK,
                message="Login successful",
                email=user["email"],
                access_token=token,
                token_type="bearer",
                temp_password=temporary_password,
                password_expired=password_expired,
                user_role=user_role_name,
                user_id=user_id,
                name=user_name,
            ).model_dump(),
        )

    except Exception:
        logger.exception("Unexpected error during login", extra={"user_id": user_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Unexpected server error"},
        )
