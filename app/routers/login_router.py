import logging
from fastapi import APIRouter, Request,Depends, status
from starlette.responses import JSONResponse, RedirectResponse

from app.schemas.login_schema import LoginRequest, LoginResponse
from app.services.login_service import simple_login
from app.config import config

from app.services.okta_sso_service import  handle_okta_callback

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login_user(login: LoginRequest):
    """
        Handle user login.
        Validates credentials, manages lockouts, and returns JWT token.
        """
    return await simple_login(login)





@router.get("/okta-sso")
async def okta_sso_login_route(request: Request):
    auth_url = (
        f"{config.OKTA_DOMAIN}/oauth2/v1/authorize?"
        f"client_id={config.OKTA_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid email profile&"
        f"redirect_uri={config.OKTA_REDIRECT_URI}&"
        f"state=random_state_123"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def okta_callback(request: Request):
    """Handles Okta redirect after successful login."""
    return await handle_okta_callback(request)




@router.get("/okta/logout")
async def okta_logout(request: Request):
    """
    Logs the user out from Okta and redirects back to frontend.
    """
    id_token = request.query_params.get("id_token")

    print("ID_TOKEN received:", id_token)

    # Frontend URL to redirect after logout
    post_logout_redirect_uri = config.LOGOUT_REDIRECT_URI

    # Okta logout URL

    issuer = config.OKTA_ISSUER
    logout_url = (
        f"{issuer}/v1/logout?"
        f"id_token_hint={id_token or ''}&"
        f"post_logout_redirect_uri={post_logout_redirect_uri}"
    )
    print("logout url is : ",logout_url)
    # Clear server-side session if any (optional)
    # request.session.clear()  # if using sessions

    return RedirectResponse(url=logout_url)
