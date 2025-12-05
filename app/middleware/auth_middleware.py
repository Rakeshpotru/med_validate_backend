import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError  # ✅ Correct import
from app.config import config
from app.utils.user_utils import fetch_user_by_email

logger = logging.getLogger(__name__)

# Public (unauthenticated) routes


PUBLIC_PATHS = [
    "/",                   # root
    "/docs",               # Swagger UI (non-root_path mode)
    "/openapi.json",       # OpenAPI schema
    "/api/docs",           # Swagger UI (root_path mode)
    "/api/openapi.json",   # OpenAPI schema (root_path mode)
    "/api/auth/login",
    "/api/transaction/getProjectFile",
    "/api/users_profile",
    "/api/transaction/getChangeRequestFile",
    "/api/forgot-password",
    "/api/verify-otp",
    "/api/reset-password",
    "/api/webhook",
    "/favicon.ico",        # include favicon too
    "/api/transaction/UploadFilesFromEditor",
    "/api/transaction/GetEditorUploadedFile"
]

# CORS defaults — match your main.py CORS middleware
CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_credentials": True
}


def add_cors_headers(response):
    """Attach CORS headers to error responses."""
    origins = CORS_CONFIG.get("allow_origins", ["*"])
    headers = CORS_CONFIG.get("allow_headers", ["*"])
    methods = CORS_CONFIG.get("allow_methods", ["*"])

    response.headers["Access-Control-Allow-Origin"] = origins[0] if origins != ["*"] else "*"
    response.headers["Access-Control-Allow-Methods"] = ", ".join(methods)
    response.headers["Access-Control-Allow-Headers"] = ", ".join(headers)
    if CORS_CONFIG.get("allow_credentials"):
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


# =====================================================
# ✅ Authentication Middleware (like get_current_user)
# =====================================================
async def auth_middleware(request: Request, call_next):
    """
    Middleware that validates JWT tokens and attaches full user info to request.state.user.
    Works like get_current_user, but applied globally.
    """
    req_path = request.url.path
    req_method = request.method

    # Allow preflight OPTIONS requests to pass through
    if req_method == "OPTIONS":
        return await call_next(request)

    logger.info(f"Incoming request: {req_method} {req_path}")

    # Skip authentication for public endpoints
    # if any(req_path.startswith(path) for path in PUBLIC_PATHS):
    #     return await call_next(request)

    if any(req_path == path or req_path.startswith(path + "/") for path in PUBLIC_PATHS):
        return await call_next(request)
    # ✅ NEW — handles both /auth/login and /api/auth/login automatically


    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning(f"Unauthorized access attempt: Missing/Invalid Authorization header for {req_path}")
        response = JSONResponse(
            status_code=401,
            content={"detail": "Authorization header missing or invalid"},
        )
        return add_cors_headers(response)

    token = auth_header.split(" ")[1]

    try:
        # Decode token
        # payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        payload = jwt.decode(
            token,
            config.SECRET_KEY,
            algorithms=[config.ALGORITHM],
            options={"verify_exp": True}  # ✅ Ensure expiration is checked
        )

        email = payload.get("sub")
        user_id = payload.get("userId")

        if not email:
            raise JWTError("Invalid token: missing subject")

        # ✅ No DB hit — user info comes directly from token
        user = {
            "email": email,
            "user_id": user_id,
            "role_id": payload.get("role_id"),
            "user_role": payload.get("user_role"),
            "user_name": payload.get("name")
        }

        request.state.user = user  # Attach to request for use in routes
        logger.info(f"Authenticated {email} (role={user.get('user_role')})")

    except ExpiredSignatureError:
        logger.warning(f"❌ Token expired for request: {req_path}")
        response = JSONResponse(status_code=401, content={"detail": "Token has expired"})
        return add_cors_headers(response)
    except JWTError as e:
        logger.error(f"❌ JWT verification failed: {str(e)}")
        response = JSONResponse(status_code=403, content={"detail": "Invalid token"})
        return add_cors_headers(response)
    except Exception as e:
        logger.exception(f"Unexpected error in auth middleware: {str(e)}")
        response = JSONResponse(status_code=500, content={"detail": "Internal server error during authentication"})
        return add_cors_headers(response)

    # Continue request if everything is valid
    return await call_next(request)