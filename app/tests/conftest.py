import os
import uuid
os.environ["ENV_STATE"] = "test"
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from app.main import app
from httpx import ASGITransport, Request, Response
from unittest.mock import AsyncMock, Mock
from app.config import config
import pytest
from datetime import datetime, timedelta, timezone
from app.db.database import database, metadata, engine
from app.security import get_password_hash
from httpx import AsyncClient
import random
import string
from app.db.transaction.users import users as users_table


# Ensure tables are created before running tests
@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    metadata.create_all(engine)
    yield
    metadata.drop_all(engine)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)


@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:
    await database.connect()
    yield
    await database.disconnect()


# @pytest.fixture()
# async def async_client(client) -> AsyncGenerator[AsyncClient, None]:
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url=client.base_url) as ac:
#         yield ac

@pytest.fixture(autouse=True)
def mock_httpx_client(mocker):
    mocked_client = mocker.patch("app.utils.email_utils.httpx.AsyncClient")

    mocked_async_client = Mock()
    response = Response(status_code=200, content="", request=Request("POST", "//"))
    mocked_async_client.post = AsyncMock(return_value=response)
    mocked_client.return_value.__aenter__.return_value = mocked_async_client

    return mocked_async_client

#------existing test cases-----------------------------------***
# Fixture: Register user manually into DB
@pytest.fixture()
async def registered_user() -> dict:
    user_details = {
        "email": "test@gmail.com",
        "password": get_password_hash("1234"),
        "user_first_name": "Test",
        "user_last_name": "User",
        "is_active": True,
        "created_date": datetime.now(),
        "created_by": str(uuid.uuid4())  # Change here: UUID string instead of int
    }
    query = users_table.insert().values(**user_details)
    user_id = await database.execute(query)
    user_details["user_id"] = user_id
    return user_details






# @pytest.fixture
# async def registered_user():
#     user_id = str(uuid.uuid4())
#     user_email = "testuser@example.com"
#     await database.execute(users_table.insert().values(
#         user_id=user_id,
#         user_email=user_email,
#         user_password="hashedpassword",
#         created_date=datetime.utcnow()
#     ))
#     return {"user_id": user_id, "user_email": user_email}

# --- Fixtures ---
@pytest.fixture(autouse=True, scope="session")
def patch_config():
    config.SECRET_KEY = "testsecretkey"
    config.ALGORITHM = "HS256"


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_unique_email():
    return f"test_{''.join(random.choices(string.ascii_lowercase, k=6))}@example.com"


@pytest.fixture
async def create_user():
    async def _create_user(
        password="StrongPassword123",
        is_active=True,
        is_locked=False,
        login_failed_count=0,
        lock_duration_minutes=20,
        password_expired=False,
        is_temporary_password=False
    ):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        password_validity_date = now - timedelta(days=91) if password_expired else now
        lock_time = now + timedelta(minutes=lock_duration_minutes) if is_locked else None

        user_email = generate_unique_email()

        query = users_table.insert().values(
            user_code="U_" + ''.join(random.choices(string.ascii_uppercase, k=4)),
            user_first_name="Test",
            user_last_name="User",
            email=user_email,
            password=get_password_hash(password),
            is_temporary_password=is_temporary_password,
            last_password_changed_date=now,
            password_validity_date=password_validity_date,
            is_active=is_active,
            login_failed_count=login_failed_count,
            is_user_locked=is_locked,
            user_locked_time=lock_time,
            created_by=1,
            created_date=now,
            updated_by=1,
            updated_date=now,
            user_address="123 Test Street"
        )

        await database.execute(query)
        return user_email

    return _create_user



@pytest.fixture
async def login_user(async_client: AsyncClient, create_user):
    async def _login_user(password="StrongPassword123", **kwargs):
        email = await create_user(password=password, **kwargs)

        response = await async_client.post("/auth/login", json={
            "user_email": email,
            "user_password": password
        })

        assert response.status_code == 200, f"Login failed for {email}: {response.text}"
        data = response.json()
        return {
            "email": email,
            "access_token": data["access_token"],
            "token_type": data["token_type"],
            "temp_password": data.get("temp_password"),
            "password_expired": data.get("password_expired")
        }

    return _login_user

# #############################################

from jose import jwt
from app.config import config
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture(scope="session")
def auth_token():
    """Generate a valid JWT for test authentication."""
    payload = {
        "sub": "testuser@example.com",
        "userId": 1,
        "role_id": 1,
        "user_role": "admin",
        "name": "Test User"
    }
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return token


@pytest.fixture
async def async_client(auth_token) -> AsyncClient:
    """Async client that automatically includes Authorization header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers.update({
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        })
        yield ac

@pytest.fixture(autouse=True)
async def auto_authorized_client(async_client):
    """Automatically make `client` available globally in tests."""
    import builtins
    builtins.client = async_client
    yield
    del builtins.client
