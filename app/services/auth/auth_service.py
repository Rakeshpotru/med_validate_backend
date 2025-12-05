# import logging
# from datetime import datetime
# from typing import Optional
#
# import httpx
# from sqlalchemy import select, insert
# from fastapi import HTTPException
#
# from app.db.database import database
# from app.db.transaction.users import users as users_table
# from app.db.transaction.user_role_mapping import user_role_mapping_table
# from app.db.master.user_roles import user_roles_table
# from app.config import config
# from app.schemas.auth.auth_schema import OktaLoginRequest
# from app.security import create_access_token
# from app.utils.user_utils import get_or_assign_role
#
# # Initialize logger
# logger = logging.getLogger(__name__)
#
#
# # -------------------------
# # Shared Helpers
# # -------------------------
# async def get_or_create_user(email: str, name: Optional[str] = None):
#     """
#     Fetch user from DB, or create if not exists.
#     """
#     try:
#         user_query = select(
#             users_table.c.user_id,
#             users_table.c.user_name,
#             users_table.c.email,
#             users_table.c.is_active,
#             users_table.c.created_date
#         ).where(users_table.c.email == email)
#
#         user = await database.fetch_one(user_query)
#
#         if not user:
#             logger.info(f"Creating new user: {email}")
#             insert_user_query = (
#                 insert(users_table)
#                 .values(
#                     user_name=name or email.split("@")[0],
#                     email=email,
#                     is_active=True,
#                     created_date=datetime.utcnow(),
#                 )
#                 .returning(
#                     users_table.c.user_id,
#                     users_table.c.user_name,
#                     users_table.c.email,
#                     users_table.c.is_active,
#                     users_table.c.created_date,
#                 )
#             )
#             user = await database.fetch_one(insert_user_query)
#
#             # Assign default role
#             await database.execute(
#                 insert(user_role_mapping_table).values(
#                     user_id=user.user_id, role_id=config.DEFAULT_ROLE_ID
#                 )
#             )
#             logger.info(f"Assigned default role {config.DEFAULT_ROLE_ID} to user {user.user_id}")
#
#         return user
#
#     except Exception as e:
#         logger.error(f"Error in _get_or_create_user: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
#
#
#
#
#
# def _build_response(user, role, extra: Optional[dict] = None):
#     """
#     Build standardized login response.
#     """
#     return {
#         "status_code": 200,
#         "message": "Login successful",
#         "data": {
#             "user_id": user.user_id,
#             "name": user.user_name,
#             "email": getattr(user, "email", None),
#             "is_active": getattr(user, "is_active", True),
#             "created_date": getattr(user, "created_date", None),
#             "role_id": getattr(role, "role_id", None),
#             "role_name": getattr(role, "role_name", None),
#             **(extra or {}),
#         },
#     }
#
#
# # -------------------------
# # Okta Login Helpers
# # -------------------------
# async def get_okta_user_by_email(email: str):
#     """
#     Fetch Okta user by email.
#     """
#     try:
#         async with httpx.AsyncClient() as client:
#             res = await client.get(
#                 f"{config.OKTA_DOMAIN}/api/v1/users?q={email}",
#                 headers={"Authorization": f"SSWS {config.OKTA_API_TOKEN}"},
#                 timeout=10
#             )
#
#         if res.status_code == 401:
#             raise HTTPException(status_code=401, detail="Invalid Okta API token")
#         if res.status_code != 200:
#             raise HTTPException(status_code=res.status_code, detail=res.text)
#
#         users = res.json()
#         if not users:
#             raise HTTPException(status_code=404, detail="User not found in Okta")
#
#         return users[0]
#
#     except httpx.RequestError as e:
#         logger.error(f"HTTPX Request Error: {e}")
#         raise HTTPException(status_code=503, detail="Okta service unavailable")
#     except Exception as e:
#         logger.error(f"Error in get_okta_user_by_email: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
#
#
# async def check_user_assignment(okta_user_id: str):
#     """
#     Verify if Okta user is assigned to the application.
#     """
#     try:
#         async with httpx.AsyncClient() as client:
#             res = await client.get(
#                 f"{config.OKTA_DOMAIN}/api/v1/apps/{config.OKTA_APP_ID}/users/{okta_user_id}",
#                 headers={"Authorization": f"SSWS {config.OKTA_API_TOKEN}"},
#                 timeout=10
#             )
#
#         if res.status_code == 404:
#             raise HTTPException(status_code=403, detail="User is not assigned to this app")
#         if res.status_code == 401:
#             raise HTTPException(status_code=401, detail="Invalid Okta API token")
#         if res.status_code != 200:
#             raise HTTPException(status_code=res.status_code, detail=res.text)
#
#         return res.json()
#
#     except httpx.RequestError as e:
#         logger.error(f"HTTPX Request Error: {e}")
#         raise HTTPException(status_code=503, detail="Okta service unavailable")
#     except Exception as e:
#         logger.error(f"Error in check_user_assignment: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
#
#
# # -------------------------
# # Okta Login Service
# # -------------------------
# async def okta_login(req: OktaLoginRequest):
#     """
#     Authenticate user via Okta, create user if not exists, assign role, and generate JWT.
#     """
#     try:
#         okta_user = await get_okta_user_by_email(req.email)
#         okta_user_id = okta_user["id"]
#         okta_profile = okta_user.get("profile", {})
#
#         if okta_user.get("status") == "PROVISIONED":
#             raise HTTPException(
#                 status_code=403,
#                 detail="User account is pending activation in Okta. Cannot login yet."
#             )
#
#         await check_user_assignment(okta_user_id)
#
#         full_name = f"{okta_profile.get('firstName', '')} {okta_profile.get('lastName', '')}".strip()
#         user = await get_or_create_user(req.email, full_name)
#         role = await get_or_assign_role(user.user_id)
# #
# #         # Generate JWT token
# #         # access_token = create_access_token(user.email)
# #         access_token = await create_access_token(dict(user))
#
#         return _build_response(
#             user,
#             role,
#             extra={
#                 "okta_sub": okta_user_id,
#                 "okta_profile": okta_profile,
#                 "isAssigned": True,
#                 "access_token": access_token,
#                 "token_type": "bearer"
#             },
#         )
#
#     except HTTPException:
#         # Already raised HTTPException, just propagate
#         raise
#     except Exception as e:
#         logger.error(f"Error in okta_login: {e}")
#         raise HTTPException(status_code=500, detail="Internal server error")
