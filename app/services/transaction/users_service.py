import logging
import os
import random
import shutil
import string
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, BackgroundTasks, status,UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select, insert, update

from passlib.hash import bcrypt
from app.db.database import database
from app.db.transaction.user_image_history import user_image_history
from app.db.transaction.users import users as users_table
from app.db.transaction.user_role_mapping import user_role_mapping_table
from app.db.master.user_roles import user_roles_table
from app.utils.email_utils import send_simple_email
from app.config import config

logger = logging.getLogger(__name__)

# -------------------- Helper Utilities -------------------- #


async def validate_user(user):
    errors = []
    # Validate role_id
    role_stmt = select(user_roles_table).where(user_roles_table.c.role_id == user.role_id)
    role = await database.fetch_one(role_stmt)
    if not role:
        errors.append(f"Invalid role_id: {user.role_id}")

    # Validate phone number (if provided)
    if user.user_phone:
        if not user.user_phone.isdigit() or len(user.user_phone) != 10 or not user.user_phone.startswith(('6', '7', '8', '9')):
            errors.append(f"Invalid phone number: {user.user_phone}")


def generate_strong_password(length: int = 8) -> str:
    if length < 4:
        raise ValueError("Password length must be at least 4 characters.")
    chars = (
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*()")
    )
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    password = list(chars + tuple(random.choices(all_chars, k=length - 4)))
    random.shuffle(password)
    return ''.join(password)

def prepare_registration_email(name: str, username: str, password: str, confirm_url: str) -> str:
    return f"""
        <p>Hello {name}!</p>
        <p>You have successfully registered.</p>
        <p><strong>Username:</strong> {username}</p>
        <p><strong>Password:</strong> {password}</p>
        <p><a href="{confirm_url}">Click here to log in</a></p>
    """

async def insert_user_role_mapping(user_id: int, role_id: int, created_by: int):
    stmt = insert(user_role_mapping_table).values(
        user_id=user_id,
        role_id=role_id,
        is_active=True,
    )
    await database.execute(stmt)


async def update_user_role_mapping(user_id: int, new_role_id: int, updated_by: Optional[int] = None):
    update_stmt = (
        user_role_mapping_table.update()
        .where(user_role_mapping_table.c.user_id == user_id)
        .values(role_id=new_role_id)
    )

    # Optional logging or auditing if updated_by is provided
    if updated_by is not None:
        update_stmt = update_stmt.values(updated_by=updated_by)

    await database.execute(update_stmt)

async def log_image_history(user_id: int, image_url: str, reason: str):
    """
    Inserts a record into user_image_history table with reason (replace/delete).
    """
    try:
        stmt = insert(user_image_history).values(
            user_id=user_id,
            image_url=image_url,
            image_changed_date=datetime.now(timezone.utc),
            reason=reason,
        )
        await database.execute(stmt)
        logger.info(f"📝 Logged image history for user_id={user_id}, reason='{reason}'")
    except Exception as e:
        logger.error(f"⚠️ Failed to log image history: {e}")




async def create_user_service(req, background_tasks: BackgroundTasks):
    """Replicates your /registeruser endpoint exactly as a service."""
    users = req.users if isinstance(req.users, list) else [req.users]
    created_user_ids, existing_users, validation_errors = [], [], []

    for user in users:
        # Validate user data
        errors = await validate_user(user)
        if errors:
            validation_errors.append({"email": user.user_email, "errors": errors})
            continue

        # Check if user already exists
        stmt = select(users_table.c.email, users_table.c.user_id, users_table.c.is_active).where(
            users_table.c.email == user.user_email
        )
        existing_user = await database.fetch_one(stmt)

        if existing_user:
            if not existing_user["is_active"]:
                # Reactivate user
                raw_password = generate_strong_password()
                hashed_password = bcrypt.hash(raw_password)
                update_stmt = (
                    users_table.update()
                    .where(users_table.c.user_id == existing_user["user_id"])
                    .values(
                        is_active=True,
                        password=hashed_password,
                        user_first_name=user.user_first_name,
                        user_middle_name=user.user_middle_name,
                        user_last_name=user.user_last_name,
                        user_name=f"{user.user_first_name} {user.user_last_name}",
                        user_phone=user.user_phone or "",
                        user_address=user.user_address,
                        is_temporary_password=True,
                        updated_by=req.created_by,
                        updated_date=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                )
                await database.execute(update_stmt)
                await update_user_role_mapping(existing_user["user_id"], user.role_id, req.created_by)
                created_user_ids.append(existing_user["user_id"])

                # Send reactivation email
                email_body = prepare_registration_email(
                    name=user.user_first_name,
                    username=user.user_email,
                    password=raw_password,
                    confirm_url=config.LOGIN_URL,
                )
                print("email_body is :",email_body);
                background_tasks.add_task(
                    send_simple_email,
                    to=user.user_email,
                    subject="Your account has been reactivated",
                    body=email_body,
                )
                logger.info(f"User reactivated: {existing_user['user_id']}")
            else:
                existing_users.append({
                    "email": user.user_email,
                    "user_first_name": user.user_first_name,
                    "user_last_name": user.user_last_name,
                    "role_id": user.role_id,
                })
            continue

        # New user creation
        raw_password = generate_strong_password()
        hashed_password = bcrypt.hash(raw_password)
        full_name = f"{user.user_first_name} {user.user_last_name}".strip()

        stmt = insert(users_table).values(
            user_first_name=user.user_first_name,
            user_middle_name=user.user_middle_name,
            user_last_name=user.user_last_name,
            email=user.user_email,
            user_name=full_name,
            user_phone=user.user_phone or "",
            password=hashed_password,
            is_temporary_password=True,
            user_address=user.user_address,
            created_by=req.created_by,
            created_date=datetime.now(timezone.utc).replace(tzinfo=None),  # ✅ Added

            is_active=req.is_active,
        ).returning(users_table.c.user_id)

        user_record = await database.fetch_one(stmt)
        if not user_record:
            logger.warning(f"User creation failed for: {user.user_email}")
            continue

        user_id = user_record["user_id"]
        created_user_ids.append(user_id)
        await insert_user_role_mapping(user_id, user.role_id, req.created_by)

        # Send welcome email
        email_body = prepare_registration_email(
            name=user.user_first_name,
            username=user.user_email,
            password=raw_password,
            confirm_url=config.LOGIN_URL,
        )
        background_tasks.add_task(
            send_simple_email,
            to=user.user_email,
            subject="Successfully signed up",
            body=email_body,
        )

    # Prepare response
    response_data = {
        "status": "success" if not existing_users and not validation_errors else "conflict",
        "status_code": status.HTTP_201_CREATED
        if not existing_users and not validation_errors
        else status.HTTP_409_CONFLICT,
        "data": {
            "created_user_ids": created_user_ids,
            "existing_users": existing_users,
            "validation_errors": validation_errors,
        },
        "message": f"{len(created_user_ids)} user(s) created, "
                   f"{len(existing_users)} user(s) already exist, "
                   f"{len(validation_errors)} user(s) failed validation.",
    }

    return JSONResponse(status_code=response_data["status_code"], content=response_data)



async def update_user_service(user_id: int, user_data):
    """
    Service to update selected fields of a user.
    """
    # Step 1: Check if user exists
    stmt = select(users_table).where(users_table.c.user_id == user_id)
    existing_user = await database.fetch_one(stmt)

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    # Step 2: Validate and prepare update data
    update_data = {}

    if user_data.user_first_name is not None:
        update_data["user_first_name"] = user_data.user_first_name
    if user_data.user_middle_name is not None:
        update_data["user_middle_name"] = user_data.user_middle_name
    if user_data.user_last_name is not None:
        update_data["user_last_name"] = user_data.user_last_name
    if user_data.user_phone is not None:
        if (not user_data.user_phone.isdigit()
            or len(user_data.user_phone) != 10
            or not user_data.user_phone.startswith(('6', '7', '8', '9'))):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format."
            )
        update_data["user_phone"] = user_data.user_phone
    if user_data.user_address is not None:
        update_data["user_address"] = user_data.user_address

    update_data["updated_by"] = user_data.updated_by
    update_data["updated_date"] = datetime.now(timezone.utc).replace(tzinfo=None)

    # Step 3: Perform the update
    if update_data:
        update_stmt = (
            users_table.update()
            .where(users_table.c.user_id == user_id)
            .values(**update_data)
        )
        await database.execute(update_stmt)
        logger.info(f"User {user_id} updated with: {update_data}")
    else:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "failed",
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "No valid update fields provided."
            }
        )

    # Step 4: Update role mapping if provided
    if user_data.role_id is not None:
        role_stmt = select(user_roles_table).where(user_roles_table.c.role_id == user_data.role_id)
        role_exists = await database.fetch_one(role_stmt)
        if not role_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role_id: {user_data.role_id}"
            )
        await update_user_role_mapping(user_id, user_data.role_id, user_data.updated_by)

    # Step 5: Return success response
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "status_code": status.HTTP_200_OK,
            "data": {"user_id": user_id},
            "message": "User updated successfully."
        }
    )

async def get_user_by_id_service(user_id: int):
    """
    Fetch a single user's details by user_id, including role info if available.
    """
    query = (
        select(
            users_table.c.user_id,
            users_table.c.user_name,
            users_table.c.email,
            users_table.c.user_phone,
            users_table.c.user_address,
            users_table.c.image_url,
            users_table.c.is_active,
            user_roles_table.c.role_id,
            user_roles_table.c.role_name
        )
        .select_from(
            users_table
            .outerjoin(user_role_mapping_table, users_table.c.user_id == user_role_mapping_table.c.user_id)
            .outerjoin(user_roles_table, user_role_mapping_table.c.role_id == user_roles_table.c.role_id)
        )
        .where(users_table.c.user_id == user_id)
    )

    user = await database.fetch_one(query)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )

    return {
        "status_code": status.HTTP_200_OK,
        "message": "User fetched successfully",
        "data": dict(user)
    }


async def update_user_service(user_id: int, user_data):
    stmt = select(users_table).where(users_table.c.user_id == user_id)
    existing_user = await database.fetch_one(stmt)

    if not existing_user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    update_data = {
        "updated_by": user_data.updated_by,
        "updated_date": datetime.now(timezone.utc)
    }

    # Basic field updates
    for field in ["user_first_name", "user_middle_name", "user_last_name", "user_address"]:
        val = getattr(user_data, field, None)
        if val is not None:
            update_data[field] = val

    if user_data.user_phone:
        if not user_data.user_phone.isdigit() or len(user_data.user_phone) != 10 or not user_data.user_phone.startswith(('6', '7', '8', '9')):
            raise HTTPException(status_code=400, detail="Invalid phone number.")
        update_data["user_phone"] = user_data.user_phone

    await database.execute(
        update(users_table).where(users_table.c.user_id == user_id).values(**update_data)
    )

    # Update role mapping if needed
    if user_data.role_id is not None:
        role = await database.fetch_one(
            select(user_roles_table).where(user_roles_table.c.role_id == user_data.role_id)
        )
        if not role:
            raise HTTPException(status_code=400, detail=f"Invalid role_id: {user_data.role_id}")
        await update_user_role_mapping(user_id, user_data.role_id)

    return JSONResponse(
        status_code=200,
        content={"status": "success", "data": {"user_id": user_id}},
    )


async def upload_user_profile_image_service(user_id: int, file: UploadFile) -> dict:
    """Uploads or replaces a user's profile image and logs it in history."""

    # ✅ Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG or PNG images are allowed.",
        )

    upload_dir = os.path.join(os.path.dirname(config.BASE_DIR), "users_profile")
    os.makedirs(upload_dir, exist_ok=True)

    # ✅ Fetch old image (if any)
    query = select(users_table.c.image_url).where(users_table.c.user_id == user_id)
    old_image = await database.fetch_one(query)

    # ✅ Generate new filename
    name, ext = os.path.splitext(file.filename)
    timestamp = int(datetime.now().timestamp())
    filename = f"{name}_{timestamp}{ext}"
    file_path = os.path.join(upload_dir, filename)

    # ✅ Record old image in history (if exists)
    if old_image and old_image["image_url"]:
        history_insert = insert(user_image_history).values(
            user_id=user_id,
            image_url=old_image["image_url"],
            image_changed_date=datetime.now(timezone.utc),
            reason="Replaced with new upload",
        )
        await database.execute(history_insert)
        logger.info(f"📝 Logged image history for user_id={user_id} (replaced)")

        # Delete old file
        old_path = os.path.join(upload_dir, old_image["image_url"])
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete old image: {e}")

    # ✅ Save new file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ Update DB
    stmt = (
        update(users_table)
        .where(users_table.c.user_id == user_id)
        .values(
            image_url=filename,
            updated_date=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    await database.execute(stmt)

    # ✅ Schema-compliant response
    return {
        "status_code": status.HTTP_200_OK,
        "message": "Profile image uploaded successfully.",
        "data": {
            "user_id": user_id,
            "image_url": filename,
        },
    }


async def delete_user_profile_image_service(user_id: int) -> dict:
    """Deletes a user's profile image and logs it in history."""

    # ✅ Fetch user image
    query = select(users_table.c.image_url).where(users_table.c.user_id == user_id)
    user = await database.fetch_one(query)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )

    if not user["image_url"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile image found for this user.",
        )

    upload_dir = os.path.join(os.path.dirname(config.BASE_DIR), "users_profile")
    image_path = os.path.join(upload_dir, user["image_url"])

    # ✅ Log deletion
    history_insert = insert(user_image_history).values(
        user_id=user_id,
        image_url=user["image_url"],
        image_changed_date=datetime.now(timezone.utc),
        reason="Deleted manually",
    )
    await database.execute(history_insert)
    logger.info(f"📝 Logged image history for user_id={user_id} (deleted manually)")

    # ✅ Delete file from disk
    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting image file: {e}",
            )

    # ✅ Nullify image in DB
    stmt = (
        update(users_table)
        .where(users_table.c.user_id == user_id)
        .values(
            image_url=None,
            updated_date=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    await database.execute(stmt)

    # ✅ Schema-compliant response
    return {
        "status_code": status.HTTP_200_OK,
        "message": "Profile image deleted successfully.",
        "data": {
            "user_id": user_id,
            "image_url": None,
        },
    }
