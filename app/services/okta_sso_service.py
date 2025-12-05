import logging
import httpx
from fastapi import Request, status
from starlette.responses import JSONResponse, RedirectResponse
from app.db.transaction.users import users as users_table
from sqlalchemy import  insert
from app.db import user_role_mapping_table
from app.schemas.login_schema import LoginResponse, AuditAction, AuditStatus
from app.utils.user_utils import fetch_user_by_email, reset_user_login_state, log_user_audit, get_user_role
from app.security import create_access_token
from app.config import config
from app.db.database import database
from datetime import datetime

logger = logging.getLogger(__name__)

# OKTA_BASE_URL = "https://yourcompany.okta.com"
# OKTA_CLIENT_ID = "your-okta-client-id"
# OKTA_REDIRECT_URI = "https://yourapp.com/api/auth/okta/callback"


async def okta_sso_login(request: Request):
    """Handles Okta SSO login flow."""
    okta_session_cookie = request.cookies.get("okta_session")

    if okta_session_cookie:
        try:
            if await validate_okta_session(okta_session_cookie):
                okta_user = await get_okta_user_info(okta_session_cookie)
                email = okta_user.get("email")

                user_record = await fetch_user_by_email(email)
                if not user_record:
                    await log_user_audit(None, AuditAction.login, AuditStatus.failure)
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"message": "User not registered in AI Verify"}
                    )

                user = dict(user_record._mapping)
                user_id = user["user_id"]
                await reset_user_login_state(user_id)
                await log_user_audit(user_id, AuditAction.login, AuditStatus.success)
                token = await create_access_token(user)
                role = await get_user_role(user_id)

                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=LoginResponse(
                        status_code=status.HTTP_200_OK,
                        message="SSO login successful",
                        email=email,
                        access_token=token,
                        token_type="bearer",
                        user_role=role["name"] if role else None,
                        user_id=user_id,
                        name=user["user_name"]
                    ).model_dump()
                )
        except Exception:
            logger.exception("Error during Okta session validation")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "SSO validation error"}
            )

    # Redirect to Okta login page if no valid session
    auth_url = (
        f"{config.OKTA_DOMAIN}/oauth2/v1/authorize?"
        f"client_id={config.OKTA_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"redirect_uri={config.OKTA_REDIRECT_URI}&"
        f"state=random_state_123"
    )
    logger.info("Redirecting user to Okta login.")
    return RedirectResponse(url=auth_url)


# --- Helper Functions ---
async def validate_okta_session(session_token: str) -> bool:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.OKTA_DOMAIN}/api/v1/sessions/me",
            headers={"Authorization": f"SSWS {session_token}"}
        )
        return resp.status_code == 200


async def get_okta_user_info(session_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{config.OKTA_DOMAIN}/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {session_token}"}
        )
        if resp.status_code == 200:
            return resp.json()
        raise Exception("Failed to fetch user info from Okta")



async def handle_okta_callback(request: Request):
    """Exchange authorization code for tokens, create user if new, and log in."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Missing authorization code"}
        )

    # --- Step 1: Exchange code for access token ---
    async with httpx.AsyncClient() as client:
        token_url = f"{config.OKTA_DOMAIN}/oauth2/v1/token"
        print("token_ur is",token_url);
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.OKTA_REDIRECT_URI,
            "client_id": config.OKTA_CLIENT_ID,
            "client_secret": config.OKTA_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = await client.post(token_url, data=data, headers=headers)
        if resp.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Failed to get token from Okta"}
            )
        tokens = resp.json()
        access_token = tokens.get("access_token")
        print("accesstoken  is",access_token);

        id_token = tokens.get("id_token")  # <--- store this
        print("idtoken  is",id_token);

    # --- Step 2: Fetch user info from Okta ---
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            f"{config.OKTA_DOMAIN}/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print("userinfo resp  is",userinfo_resp);
        print("userinfo url   is",f"{config.OKTA_DOMAIN}/oauth2/v1/userinfo");


        if userinfo_resp.status_code != 200:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Failed to get user info"}
            )

        userinfo = userinfo_resp.json()
        email = userinfo.get("email")
        first_name = userinfo.get("given_name") or ""
        last_name = userinfo.get("family_name") or ""
        full_name = userinfo.get("name") or f"{first_name} {last_name}"

    # --- Step 3: Lookup or create user ---
    user_record = await fetch_user_by_email(email)
    if not user_record:
        try:
            logger.info(f"Creating new user from Okta login: {email}")
            insert_user_query = (
                insert(users_table)
                .values(
                    user_name=full_name,
                    email=email,
                    user_first_name=first_name,
                    user_last_name=last_name,
                    is_active=True,
                    created_date=datetime.utcnow(),
                )
                .returning(
                    users_table.c.user_id,
                    users_table.c.user_name,
                    users_table.c.user_first_name,
                    users_table.c.user_last_name
                )
            )
            user_record = await database.fetch_one(insert_user_query)

            # Assign default role
            await database.execute(
                insert(user_role_mapping_table).values(
                    user_id=user_record.user_id,
                    role_id=config.DEFAULT_ROLE_ID
                )
            )
            logger.info(f"Assigned default role ID {config.DEFAULT_ROLE_ID} to new user {user_record.user_id}")

        except Exception as e:
            logger.exception("Error creating new Okta user")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Failed to create new Okta user"}
            )

    # --- Step 4: Login flow ---
    user = dict(user_record._mapping) if hasattr(user_record, "_mapping") else dict(user_record)
    user_id = user["user_id"]
    user["email"] = email
    user["user_name"] = user.get("user_name") or full_name
    user["first_name"] = first_name
    user["last_name"] = last_name

    await reset_user_login_state(user_id)
    await log_user_audit(user_id, AuditAction.login, AuditStatus.success)
    token = await create_access_token(user)
    role = await get_user_role(user_id)

    # --- Step 5: Redirect to frontend ---
    # frontend_url = f"http://localhost:5173/login-success?token={token}"
    # logger.info(f"Redirecting Okta user {email} to frontend: {frontend_url}")
    # return RedirectResponse(url=frontend_url)

    frontend_url = f"{config.FRONTEND_LOGOUT_REDIRECT_URI}?token={token}&id_token={id_token}"
    logger.info(f"Redirecting Okta user {email} to frontend: {frontend_url}")
    return RedirectResponse(url=frontend_url)


