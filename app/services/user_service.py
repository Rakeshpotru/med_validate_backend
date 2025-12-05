# import logging
# from datetime import datetime, timedelta,  timezone
# from fastapi import  status
# from starlette.responses import JSONResponse
# from app.db.database import  database, users_table, user_audit
# # from app.db.database import users_table, user_audit
# # from app.models.users import  user_audit
# from app.schemas.user_schema import AuditStatus, AuditAction, UserLoginResponse
# from app.security import create_access_token, verify_password
# from app.utils.user_utils import fetch_user_by_email
#
# naive_utc_time = datetime.now(timezone.utc).replace(tzinfo=None)
# MAX_FAILED_ATTEMPTS = 5
# LOCK_DURATION_MINUTES = 20
# PASSWORD_EXPIRY_DAYS = 90
# # db: AsyncSession
#
#
# # Configure logger
# logger = logging.getLogger(__name__)
#
#
# async def log_user_audit(user_id: int | None,  action: AuditAction,status: AuditStatus):
#     logger.info(f"Logging audit: user_id={user_id}, action={action}, status={status}")
#     query = user_audit.insert().values(
#         user_id=user_id,
#         action=action.value,  # use enum values
#         status=status.value,
#         timestamp=naive_utc_time
#     )
#     await database.execute(query)
#
#
# async def reset_user_login_state(user_id: int):
#     logger.info(f"Resetting login state for user: {user_id}")
#     await database.execute(
#         users_table.update()
#         .where(users_table.c.user_id == user_id)
#         .values(
#             login_failed_count=0,
#             is_user_locked=False,
#             user_locked_time=None
#         )
#     )
#
# def check_password_expiry_flag(password_validity_date: datetime | None) -> bool:
#     if password_validity_date is None:
#         logger.info("Password validity date is None — skipping expiry check.")
#         return False
#
#     now = naive_utc_time
#     expired = (now - password_validity_date).days >= PASSWORD_EXPIRY_DAYS
#
#     if expired:
#         logger.warning(f"Password expired. Validity date: {password_validity_date}")
#     else:
#         logger.info(f"Password still valid. Validity date: {password_validity_date}")
#
#     return expired
#
# async def user_login_details(login):
#     now = datetime.now(timezone.utc).replace(tzinfo=None)
#     logger.debug("Authenticating user", extra={"email":login.user_email})
#     # logger.info(f"Login attempt for email: {login.user_email}")
#     user_record = await fetch_user_by_email(login.user_email)
#     if not user_record:
#         # logger.warning(f"Login failed — user not found: {login.user_email}")
#         logger.warning("Authenticating user", extra={"email": login.user_email})
#
#         await log_user_audit(None, AuditAction.login, AuditStatus.failure)
#         return JSONResponse(
#             status_code=status.HTTP_403_FORBIDDEN,
#             content=UserLoginResponse(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 message="Invalid credentials"
#             ).model_dump()
#         )
#
#     user = dict(user_record)
#     logger.debug(f"User record fetched: {user['user_id']}")
#     failed_attempts = user.get("login_failed_count") or 0
#     is_locked = user.get("is_user_locked") or False
#     locked_time = user.get("user_locked_time")
#     temporary_password = user.get("is_temporary_password")
#
#     # Case 1: Already locked and still within lock duration
#     if is_locked and locked_time and now < locked_time:
#         logger.warning(f"Login blocked — user account is locked: {user['user_id']}")
#         await log_user_audit(int(user["user_id"]), AuditAction.login, AuditStatus.failure)
#         remaining_lock_duration = int((locked_time - now).total_seconds() // 60)
#         return JSONResponse(
#             status_code=status.HTTP_403_FORBIDDEN,
#             content=UserLoginResponse(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 message=f"Account is temporarily locked. Try again after {remaining_lock_duration} minutes."
#             ).model_dump()
#         )
#
#
#     # Case 2: Password is incorrect
#     if not verify_password(login.user_password, user["user_password"]):
#         logger.warning(f"Invalid password for user: {user['user_id']} (Attempts: {failed_attempts})")
#         if failed_attempts >= MAX_FAILED_ATTEMPTS:
#             logger.warning(f"Account lock extended due to invalid login after expiry: {user['user_id']}")
#             await database.execute(
#                 users_table.update()
#                 .where(users_table.c.user_id == user["user_id"])
#                 .values(user_locked_time=now + timedelta(minutes=LOCK_DURATION_MINUTES))
#             )
#         else:
#             failed_attempts += 1
#             lock_required = failed_attempts >= MAX_FAILED_ATTEMPTS
#             lock_time = now + timedelta(minutes=LOCK_DURATION_MINUTES) if lock_required else None
#
#             logger.info(f"Updating failed login. Attempts: {failed_attempts}, Lock Required: {lock_required}")
#             await database.execute(
#                 users_table.update()
#                 .where(users_table.c.user_id == user["user_id"])
#                 .values(
#                     login_failed_count=min(failed_attempts, MAX_FAILED_ATTEMPTS),
#                     is_user_locked=lock_required,
#                     user_locked_time=lock_time
#                 )
#             )
#
#         await log_user_audit(int(user["user_id"]), AuditAction.login, AuditStatus.failure)
#
#         if failed_attempts >= MAX_FAILED_ATTEMPTS:
#             logger.error(f"Account locked due to repeated failed attempts: {user['user_id']}")
#
#             return JSONResponse(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 content=UserLoginResponse(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     message="Account locked due to multiple failed login attempts.. for 20 minutes"
#                 ).model_dump()
#             )
#
#
#
#         else:
#             remaining_attempts = max(0, MAX_FAILED_ATTEMPTS - failed_attempts)
#             logger.info(f"Invalid credentials. Remaining attempts: {remaining_attempts}")
#
#             return JSONResponse(
#             status_code=status.HTTP_403_FORBIDDEN,
#             content=UserLoginResponse(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 message= "Invalid credentials",
#                 remaining_attempts= remaining_attempts
#
#             ).model_dump()
#         )
#     password_expired = check_password_expiry_flag(user.get("password_validity_date"))
#
#     # Case 3: Password is correct
#     logger.info(f"Login successful for user: {user['user_id']}")
#     await reset_user_login_state(int(user["user_id"]))
#     await log_user_audit(int(user["user_id"]), AuditAction.login, AuditStatus.success)
#
#     token = create_access_token(login.user_email)
#     logger.info(f"Access token issued for user: {user['user_id']}")
#
#     return JSONResponse(
#     status_code=status.HTTP_200_OK,
#     content=UserLoginResponse(
#         status_code=status.HTTP_200_OK,
#         message="Login successful",
#         email=user["user_email"],
#         access_token=token,
#         token_type="bearer",
#         temp_password=temporary_password,
#         password_expired=password_expired
#     ).model_dump()
# )