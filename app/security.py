from datetime import datetime, timedelta, timezone
import logging
from jose import jwt, ExpiredSignatureError, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from app.config import config
from app.utils.user_utils import fetch_user_by_email, get_user_role

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"])

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def create_access_token(user: dict) -> str:
    # expire = datetime.now(timezone.utc) + timedelta(seconds=1800)  # for testing
    expire = datetime.now(timezone.utc) + timedelta(days=7)

    role = await get_user_role(user["user_id"])

    jwt_data = {
        "sub": user["email"],
        "userId": user["user_id"],
        "role_id": role["id"],
        "name": user.get("user_name"),
        "user_role": role["name"] if role else None,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }

    return jwt.encode(jwt_data, key=config.SECRET_KEY, algorithm=config.ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, key=config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

    user = await fetch_user_by_email(email=email)
    if user is None:
        raise credentials_exception

    # Convert Record to dict
    user = dict(user)

    # Attach values from token payload
    user["role_id"] = payload.get("role_id")
    user["user_id"] = payload.get("userId")
    user["user_role"] = payload.get("user_role")
    user["user_name"] = payload.get("name")

    return user

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
