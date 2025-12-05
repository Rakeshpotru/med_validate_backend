import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.db.database import database
from app.db.transaction.user_password_history import user_password_history
from app.db.transaction.user_otp import user_otp
from app.db.transaction.users import users as users_table
from app.security import get_password_hash
from app.utils.db_transaction import with_transaction
from app.utils.email_utils import send_simple_email
from app.utils.validations import (
    generate_otp,
    validate_password,
    is_password_reused,
    validate_user_account
)

from app.schemas.forgot_password_schema import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyOtpRequest,
    SendResetResponse
)
from app.utils.messages import messages

# Logger setup
logger = logging.getLogger(__name__)

# Email template and constants
# TEMPLATE_OTP = os.getenv("SENDGRID_TEMPLATE_OTP")
OTP_VALIDITY_MINUTES = 10



def build_forgot_password_email(username: str, otp: str, expiry: int) -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 10px; padding: 20px; box-shadow: 0px 0px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #333333;">Password Reset Request</h2>
            <p>Hi <strong>{username}</strong>,</p>
            <p>You requested to reset your password. Use the OTP below to complete the process:</p>
            <h3 style="color: #1a73e8;">{otp}</h3>
            <p>This OTP is valid for <strong>{expiry} minutes</strong>.</p>
            <p>If you didn't request this, you can safely ignore this email.</p>
            <br/>
            <p style="font-size: 14px; color: #888888;">Thank you,<br/>Your Support Team</p>
        </div>
    </body>
    </html>
    """
async def process_forgot_password(request: ForgotPasswordRequest) -> SendResetResponse:
    """
    Handles forgot password logic:
    - Validate user
    - Generate OTP
    - Update or insert OTP into DB
    - Send OTP via email
    """
    try:
        email = request.email

        # Step 1: Fetch user by email
        query = users_table.select().where(users_table.c.email == email)
        user = await database.fetch_one(query)

        validate_user_account(user)

        user_id = user["user_id"]
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=OTP_VALIDITY_MINUTES)

        # expiry = (now + timedelta(minutes=OTP_VALIDITY_MINUTES)).replace(tzinfo=None)

        # Step 2: Generate new OTP
        otp = generate_otp()

        # Step 3: Check for existing OTP record
        existing_otp_query = user_otp.select().where(user_otp.c.user_id == user_id)
        existing_otp = await database.fetch_one(existing_otp_query)

        if existing_otp:
            # Update existing OTP record
            update_query = user_otp.update().where(
                user_otp.c.user_id == user_id
            ).values(
                otp=otp,
                otp_expiry_date=expiry,
                updated_at=now
            )
            await database.execute(update_query)
            logger.info(f"Updated OTP for user_id={user_id}")
        else:
            # Insert new OTP record
            insert_query = user_otp.insert().values(
                user_id=user_id,
                otp=otp,
                otp_expiry_date=expiry,
                created_date=now
            )
            await database.execute(insert_query)
            logger.info(f"Inserted new OTP for user_id={user_id}")

        # Step 4: Send OTP email
        # await send_template_email(
        #     to_email=email,
        #     template_id=TEMPLATE_OTP,
        #     dynamic_data={
        #         "otp": otp,
        #         "expiry": f"{OTP_VALIDITY_MINUTES} minutes",
        #         "username": user["user_first_name"] or user["email"]
        #     }
        # )

        html_body = build_forgot_password_email(
            username=user["user_first_name"] or user["email"],
            otp=otp,
            expiry=OTP_VALIDITY_MINUTES
        )
        await send_simple_email(
            to=email,
            subject="Your Password Reset OTP",
            body=html_body
        )

        return SendResetResponse(status_code=status.HTTP_200_OK,message=messages["otp_sent"],user_id=user_id)

    except HTTPException as http_exc:
        logger.warning(f"User-related error: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        logger.error(f"Unhandled error in forgot_password: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=messages["internal_error"]
        )


async def process_verify_otp(request: VerifyOtpRequest) -> SendResetResponse:
    """
    Verifies OTP for the given user_id
    """
    try:
        otp_input = request.otp.strip()
        if not otp_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,

                detail=messages["otp_required"]
            )

        query = user_otp.select().where((user_otp.c.user_id == request.user_id))
        otp_record = await database.fetch_one(query)

        if not otp_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=messages["otp_missing"])

        if otp_record["otp"] != otp_input:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=messages["otp_incorrect"])

        # expiry = otp_record["otp_expiry_date"]
        expiry: datetime = otp_record["otp_expiry_date"]

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=messages["otp_expired"])

        logger.info(f"OTP verified successfully for user_id: {request.user_id}")
        return SendResetResponse(status_code=status.HTTP_200_OK,message=messages["otp_verified"],user_id=request.user_id)

    except HTTPException as http_exc:
        logger.warning(f"OTP verification failed: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=messages["internal_error"]
        )

@with_transaction
async def process_reset_password(request: ResetPasswordRequest) -> SendResetResponse:
    """
    Reset user's password after OTP verification.

    Steps:
    - Validate new password strength and confirm match.
    - Prevent reuse of previous 5 passwords.
    - Update user's password and password history.
    """

    try:
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=messages["password_mismatch"]
            )

        # Fetch user
        query = users_table.select().where(users_table.c.user_id == request.user_id)
        user = await database.fetch_one(query)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=messages["user_not_found"])

        # Validate new password strength
        if not validate_password(request.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=messages["weak_password"]
            )

        # Check password reuse (last 5 passwords)
        if await is_password_reused(user_id=request.user_id, plain_password=request.new_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=messages["password_reuse"]
            )

        # now = datetime.now(timezone.utc).replace(tzinfo=None)
        now = datetime.now(timezone.utc)

        hashed_password = get_password_hash(request.new_password)
        validity_date = (now + timedelta(days=90)).replace(tzinfo=None)

        # Update user password
        update_query = users_table.update().where(users_table.c.user_id == request.user_id).values(
            password=hashed_password,
            last_password_changed_date=now,
            password_validity_date=validity_date,
            updated_date=now,
            updated_by=request.user_id
        )
        await database.execute(update_query)




        # Log password change history
        insert_history = user_password_history.insert().values(
            user_id=request.user_id,
            old_password=hashed_password,
            password_changed_date=now
        )
        await database.execute(insert_history)

        logger.info(f"Password reset successfully for user_id: {request.user_id}")
        return SendResetResponse(status_code=status.HTTP_200_OK,message=messages["reset_success"])

    except HTTPException as http_exc:
        logger.warning(f"Password reset error: {http_exc.detail}")
        raise http_exc

    except Exception as e:
        logger.error(f"Unhandled error during password reset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=messages["internal_error"]
        )
