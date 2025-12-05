# import logging
# import random
# import string
# from typing import List, Optional
#
# from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Query, status
# from sqlalchemy import select, insert
# from passlib.hash import bcrypt
# from datetime import datetime, timezone
#
#
# from app.db.database import database
# from app.db.transaction.users import users as users_table
# from app.db.transaction.user_role_mapping import user_role_mapping_table
# from app.db.master.user_roles import user_roles_table
# from app.schemas.users import UserRequest, UserResponse, UserUpdateRequest
# from app.config import config
# from fastapi.responses import JSONResponse
# from fastapi.encoders import jsonable_encoder
# from app.utils.db_transaction import with_transaction
# from app.utils.email_utils import send_simple_email  # For sending email notifications
#
# # Define the path to Excel file
# EXCEL_FILE_PATH = "app/utils/files/User_Role_Template.xlsx"
#
#
# # Logger setup
# logger = logging.getLogger(__name__)
# router = APIRouter(prefix="/users_poc", tags=["Users"])
#
# # -------------------- Utilities -------------------- #
#
# def generate_strong_password(length: int = 8) -> str:
#     """
#     Generate a strong password consisting of at least one of
#     lowercase letter, uppercase letter, digit, character
#     """
#     if length < 4:
#         raise ValueError("Password length must be at least 4 characters.")
#
#     # Ensure that the password includes at least one of each required character set
#     chars = (
#         random.choice(string.ascii_lowercase),
#         random.choice(string.ascii_uppercase),
#         random.choice(string.digits),
#         random.choice("!@#$%^&*()")
#     )
#     all_chars = string.ascii_letters + string.digits + "!@#$%^&*()"
#     password = list(chars + tuple(random.choices(all_chars, k=length - 4)))
#     random.shuffle(password)  # Shuffle to ensure randomness
#     return ''.join(password)
#
#
# def prepare_registration_email(name: str, username: str, password: str, confirm_url: str) -> str:
#     """
#     Prepare the content of the registration email to send to the user.
#     """
#     return f"""
#         <p>Hello {name}!</p>
#         <p>You have successfully registered.</p>
#         <p><strong>Username:</strong> {username}</p>
#         <p><strong>Password:</strong> {password}</p>
#         <p><a href="{confirm_url}">Click here to log in</a></p>
#     """
#
#
# async def insert_user_role_mapping(user_id: int, role_id: int, created_by: int):
#     """
#     Insert user-role mapping into the database for user-role association.
#     """
#     stmt = insert(user_role_mapping_table).values(
#         user_id=user_id,
#         role_id=role_id,
#         is_active=True,
#     )
#     await database.execute(stmt)
#
# async def update_user_role_mapping(user_id: int, new_role_id: int, updated_by: int):
#     """
#     Update the role of the user in the user_role_mapping table.
#
#     Parameters:
#         user_id,new_role_id,updated_by
#     """
#     update_stmt = (
#         user_role_mapping_table.update()
#         .where(user_role_mapping_table.c.user_id == user_id)
#         .values(
#             role_id=new_role_id,
#             updated_by=updated_by,  # Assuming req.created_by is the user performing the update
#             updated_date= datetime.now(timezone.utc).replace(tzinfo=None)  # Current UTC timestamp without timezone
#         )
#     )
#
#     await database.execute(update_stmt)
#     logger.info(f"User role updated for user_id {user_id} to new role_id {new_role_id}.")
#
# # -------------------- API Routes -------------------- #
#
# async def validate_user(user):
#     errors = []
#     # Validate role_id
#     role_stmt = select(user_roles_table).where(user_roles_table.c.role_id == user.role_id)
#     role = await database.fetch_one(role_stmt)
#     if not role:
#         errors.append(f"Invalid role_id: {user.role_id}")
#
#     # Validate phone number (if provided)
#     if user.user_phone:
#         if not user.user_phone.isdigit() or len(user.user_phone) != 10 or not user.user_phone.startswith(('6', '7', '8', '9')):
#             errors.append(f"Invalid phone number: {user.user_phone}")
#
#
# @router.post("/registeruser", status_code=status.HTTP_201_CREATED)
# async def register_user(req: UserRequest, background_tasks: BackgroundTasks, request: Request):
#     users = req.users if isinstance(req.users, list) else [req.users]
#     created_user_ids, existing_users, validation_errors = [], [], []
#
#     for user in users:
#         # Validate user data
#         errors = await validate_user(user)
#         if errors:
#             validation_errors.append({"email": user.user_email, "errors": errors})
#             continue
#
#         # Check if user already exists
#         stmt = select(users_table.c.email, users_table.c.user_id, users_table.c.is_active).where(
#             users_table.c.email == user.user_email
#         )
#         existing_user = await database.fetch_one(stmt)
#
#         if existing_user:
#             if not existing_user["is_active"]:
#                 # Reactivate user
#                 raw_password = generate_strong_password()
#                 hashed_password = bcrypt.hash(raw_password)
#                 update_stmt = (
#                     users_table.update()
#                     .where(users_table.c.user_id == existing_user["user_id"])
#                     .values(
#                         is_active=True,
#                         password=hashed_password,
#                         user_first_name=user.user_first_name,
#                         user_middle_name=user.user_middle_name,
#                         user_last_name=user.user_last_name,
#                         user_name=f"{user.user_first_name} {user.user_last_name}",
#                         user_phone=user.user_phone or "",
#                         user_address=user.user_address,
#                         is_temporary_password=True,
#                         updated_by=req.created_by,
#                         updated_date=datetime.now(timezone.utc).replace(tzinfo=None)
#                     )
#                 )
#                 await database.execute(update_stmt)
#                 await update_user_role_mapping(existing_user["user_id"], user.role_id, req.created_by)
#                 created_user_ids.append(existing_user["user_id"])
#
#                 # Send reactivation email
#                 email_body = prepare_registration_email(
#                     name=user.user_first_name,
#                     username=user.user_email,
#                     password=raw_password,
#                     confirm_url=config.LOGIN_URL
#                 )
#                 background_tasks.add_task(
#                     send_simple_email,
#                     to=user.user_email,
#                     subject="Your account has been reactivated",
#                     body=email_body
#                 )
#                 logger.info(f"User reactivated: {existing_user['user_id']}")
#             else:
#                 existing_users.append({
#                     "email": user.user_email,
#                     "user_first_name": user.user_first_name,
#                     "user_last_name": user.user_last_name,
#                     "role_id": user.role_id
#                 })
#             continue
#
#         # New user creation
#         raw_password = generate_strong_password()
#         hashed_password = bcrypt.hash(raw_password)
#
#         full_name = f"{user.user_first_name} {user.user_last_name}".strip()
#
#         stmt = insert(users_table).values(
#             user_first_name=user.user_first_name,
#             user_middle_name=user.user_middle_name,
#             user_last_name=user.user_last_name,
#             email=user.user_email,
#             user_name=full_name,
#
#             user_phone=user.user_phone or "",
#             password=hashed_password,
#             is_temporary_password=True,
#             user_address=user.user_address,
#             created_by=req.created_by,
#             is_active=req.is_active
#         ).returning(users_table.c.user_id)
#
#         user_record = await database.fetch_one(stmt)
#         if not user_record:
#             logger.warning(f"User creation failed for: {user.user_email}")
#             continue
#
#         user_id = user_record["user_id"]
#         created_user_ids.append(user_id)
#         await insert_user_role_mapping(user_id, user.role_id, req.created_by)
#
#         # Send welcome email
#         email_body = prepare_registration_email(
#             name=user.user_first_name,
#             username=user.user_email,
#             password=raw_password,
#             confirm_url=config.LOGIN_URL
#         )
#         background_tasks.add_task(
#             send_simple_email,
#             to=user.user_email,
#             subject="Successfully signed up",
#             body=email_body
#         )
#
#     # Prepare response
#     response_data = {
#         "status": "success" if not existing_users and not validation_errors else "conflict",
#         "status_code": status.HTTP_201_CREATED if not existing_users and not validation_errors else status.HTTP_409_CONFLICT,
#         "data": {
#             "created_user_ids": created_user_ids,
#             "existing_users": existing_users,
#             "validation_errors": validation_errors
#         },
#         "message": f"{len(created_user_ids)} user(s) created, {len(existing_users)} user(s) already exist, {len(validation_errors)} user(s) failed validation."
#     }
#
#     return JSONResponse(status_code=response_data["status_code"], content=response_data)
#
# @router.get(
#     "/getusers",
#     response_model=List[UserResponse],
#     status_code=status.HTTP_200_OK,
#     summary="Get users",
#     description="Retrieve users by filters like ID, email, and active status."
# )
# async def get_users(
#     user_id: Optional[int] = Query(None, description="Filter by user ID"),
#     user_email: Optional[str] = Query(None, description="Filter by user email"),
#     is_active: Optional[bool] = Query(None, description="Filter by active status"),
# ):
#     """
#     Retrieve users based on the provided filters (user_id, user_email, and is_active).
#     """
#     stmt = select(users_table).order_by(users_table.c.user_id)
#
#     if user_id is not None:
#         stmt = stmt.where(users_table.c.user_id == user_id)
#     if user_email is not None:
#         stmt = stmt.where(users_table.c.user_email == user_email)
#     if is_active is not None:
#         stmt = stmt.where(users_table.c.is_active == is_active)
#     else:
#         stmt = stmt.where(users_table.c.is_active == True)
#
#     rows = await database.fetch_all(stmt)
#     users = [dict(row) for row in rows]
#     safe_data = jsonable_encoder(users)  # Safely encode any datetime or non-serializable objects
#
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={
#             "status": "success",
#             "status_code": status.HTTP_200_OK,
#             "data": safe_data,
#             "message": f"{len(rows)} user(s) found"
#         }
#     )
#
# # To delete a existing user
# @router.delete(
#     "/deleteuser/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Soft delete a user",
#     description="Set is_active to False for the specified user"
# )
# async def delete_user(
#     user_id: int,
#     request: Request
# ):
#     """
#     Soft delete a user by setting `is_active` to False.
#     """
#     # Check if user exists
#     stmt = select(users_table.c.user_id, users_table.c.is_active).where(users_table.c.user_id == user_id)
#     user = await database.fetch_one(stmt)
#
#      # If the user doesn't exist, return HTTP 404 Not Found
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"User with id {user_id} not found."
#         )
#
#     # If the user is already deactivated (is_active is False), return a conflict response
#     if not user["is_active"]:
#         return JSONResponse(
#             status_code=status.HTTP_409_CONFLICT,
#             content={
#                 "status": "conflict",
#                 "status_code": status.HTTP_409_CONFLICT,
#                 "data": {"user_id": user_id},
#                 "message": f"User {user_id} is already Deleted."
#             }
#         )
#
#     # Perform soft delete (mark user as inactive)
#     update_stmt = (
#         users_table.update()
#         .where(users_table.c.user_id == user_id)
#         .values(is_active=False)
#     )
#
#     await database.execute(update_stmt)
#     logger.info(f"User {user_id} marked as inactive")
#
#     # Return success response after deactivating the user
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={
#             "status": "success",
#             "status_code": status.HTTP_200_OK,
#             "data": {"user_id": user_id},
#             "message": f"User {user_id} has been deactivated."
#         }
#     )
#
#
# @router.put(
#     "/updateuser/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Update user fields",
#     description="Update selected fields for an existing user by user_id"
# )
# async def update_user(
#     user_id: int,
#     user_data: UserUpdateRequest,  # Using Pydantic model for request body validation
# ):
#     """
#     Update selected user fields if they are provided in the request.
#     """
#     # Step 1: Check if user exists
#     stmt = select(users_table).where(users_table.c.user_id == user_id)
#     existing_user = await database.fetch_one(stmt)
#
#     if not existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"User with id {user_id} not found."
#         )
#
#     # Step 2: Prepare values to update
#     update_data = {}
#     if user_data.user_first_name is not None:
#         update_data["user_first_name"] = user_data.user_first_name
#     if user_data.user_middle_name is not None:
#         update_data["user_middle_name"] = user_data.user_middle_name
#     if user_data.user_last_name is not None:
#         update_data["user_last_name"] = user_data.user_last_name
#     if user_data.user_phone is not None:
#         if not user_data.user_phone.isdigit() or len(user_data.user_phone) != 10 or not user_data.user_phone.startswith(('6', '7', '8', '9')):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid phone number format."
#             )
#         update_data["user_phone"] = user_data.user_phone
#     if user_data.user_address is not None:
#         update_data["user_address"] = user_data.user_address
#
#     # Add audit fields
#     update_data["updated_by"] = user_data.updated_by
#     update_data["updated_date"] = datetime.now(timezone.utc).replace(tzinfo=None)
#
#     # Step 3: Perform update if any data provided
#     if update_data:
#         update_stmt = (
#             users_table.update()
#             .where(users_table.c.user_id == user_id)
#             .values(**update_data)
#             )
#         await database.execute(update_stmt)
#         logger.info(f"User {user_id} updated with: {update_data}")
#     else:
#         return JSONResponse(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             content={
#                 "status": "failed",
#                 "status_code": status.HTTP_400_BAD_REQUEST,
#                 "message": "No valid update fields provided."
#             }
#         )
#
#     # Step 4: If role_id is passed, update mapping
#     if user_data.role_id is not None:
#         role_stmt = select(user_roles_table).where(user_roles_table.c.role_id == user_data.role_id)
#         role_exists = await database.fetch_one(role_stmt)
#         if not role_exists:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=f"Invalid role_id: {user_data.role_id}"
#             )
#         await update_user_role_mapping(user_id, user_data.role_id, user_data.updated_by)
#
#     return JSONResponse(
#         status_code=status.HTTP_200_OK,
#         content={
#             "status": "success",
#             "status_code": status.HTTP_200_OK,
#             "data": {"user_id": user_id},
#             "message": "User updated successfully."
#         }
#     )