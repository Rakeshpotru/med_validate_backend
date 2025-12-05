import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from fastapi.responses import RedirectResponse, JSONResponse

from app.services.okta_sso_service import (
    validate_okta_session,
    get_okta_user_info,
    handle_okta_callback,
)


# --- Helper Mock Request ---
class MockRequest:
    def __init__(self, cookies=None, query_params=None):
        self.cookies = cookies or {}
        self.query_params = query_params or {}


# -------------------------------
# Tests
# -------------------------------

@pytest.mark.anyio
async def test_validate_okta_session_true(mocker):
    """validate_okta_session returns True when status 200"""
    mock_resp = MagicMock(status_code=200)

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    result = await validate_okta_session("fake-session")
    assert result is True


@pytest.mark.anyio
async def test_validate_okta_session_false(mocker):
    """validate_okta_session returns False when status != 200"""
    mock_resp = MagicMock(status_code=403)

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    result = await validate_okta_session("fake-session")
    assert result is False


@pytest.mark.anyio
async def test_get_okta_user_info_success(mocker):
    """get_okta_user_info returns JSON dict"""
    data = {"email": "john@example.com"}
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = data

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    result = await get_okta_user_info("fake-token")
    assert result == data


@pytest.mark.anyio
async def test_get_okta_user_info_failure(mocker):
    """get_okta_user_info raises exception when status != 200"""
    mock_resp = MagicMock(status_code=403)
    mock_resp.json.return_value = {}

    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_resp)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    import pytest

    with pytest.raises(Exception, match="Failed to fetch user info from Okta"):
        await get_okta_user_info("fake-token")


@pytest.mark.anyio
async def test_handle_okta_callback_missing_code():
    """Missing code in query_params returns 400 JSONResponse"""
    request = MockRequest(query_params={})
    response = await handle_okta_callback(request)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    body = response.body.decode()
    assert "Missing authorization code" in body


@pytest.mark.anyio
async def test_handle_okta_callback_success(mocker):
    """Successful Okta callback returns RedirectResponse"""
    request = MockRequest(query_params={"code": "abc123", "state": "state123"})

    # Mock Okta API responses
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    token_resp = MagicMock(status_code=200)
    token_resp.json.return_value = {"access_token": "token123", "id_token": "id_abc"}
    userinfo_resp = MagicMock(status_code=200)
    userinfo_resp.json.return_value = {
        "email": "john@example.com",
        "given_name": "John",
        "family_name": "Doe",
    }

    mock_client.post = AsyncMock(return_value=token_resp)
    mock_client.get = AsyncMock(return_value=userinfo_resp)
    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    # Mock DB / utils
    mock_user = MagicMock()
    mock_user._mapping = {"user_id": 1, "user_name": "John Doe"}
    mocker.patch("app.services.okta_sso_service.fetch_user_by_email", AsyncMock(return_value=mock_user))
    mocker.patch("app.services.okta_sso_service.reset_user_login_state", AsyncMock())
    mocker.patch("app.services.okta_sso_service.log_user_audit", AsyncMock())
    mocker.patch("app.services.okta_sso_service.create_access_token", AsyncMock(return_value="jwt_token"))
    mocker.patch("app.services.okta_sso_service.get_user_role", AsyncMock(return_value={"name": "Admin"}))

    # 👇 Fix here
    mocker.patch("app.services.okta_sso_service.config.FRONTEND_LOGOUT_REDIRECT_URI", "http://localhost:5173/login-success")

    response = await handle_okta_callback(request)

    assert isinstance(response, RedirectResponse)
    assert "login-success" in response.headers["location"]
    assert "jwt_token" in response.headers["location"]

