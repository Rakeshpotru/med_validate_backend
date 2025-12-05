# from fastapi import APIRouter, Depends
# from app.schemas.auth.auth_schema  import OktaLoginRequest
# from app.services.auth.auth_service import okta_login  # Assuming your okta_login function is in login_service.py
#
# router = APIRouter(
#     prefix="/auth",
#     tags=["Authentication"]
# )
#
# @router.post("/okta-login")
# async def login_with_okta(req: OktaLoginRequest):
#     """
#     Authenticate a user via Okta.
#     """
#     return await okta_login(req)
