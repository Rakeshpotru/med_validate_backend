# import pytest
# from httpx import AsyncClient
# from app.db import database
# from app.db.database import database, users_table
#
#
# # --- Helper functions ---
#
# async def login_request(async_client: AsyncClient, email: str, password: str):
#     return await async_client.post("/login", json={
#         "user_email": email,
#         "user_password": password
#     })
#
#
# def assert_invalid_credentials_response(response):
#     assert response.status_code == 403
#     data = response.json()
#     assert data["status_code"] == 403
#     assert data["message"] == "Invalid credentials"
#     assert "remaining_attempts" in data
#
#
# # --- Test cases ---
#
# @pytest.mark.anyio
# async def test_successful_login(login_user):
#     user = await login_user()
#     assert user["access_token"]
#     assert user["temp_password"] is False
#     assert user["password_expired"] is False
#
#
# @pytest.mark.anyio
# async def test_login_invalid_password(async_client: AsyncClient, create_user):
#     email = await create_user(password="CorrectPassword123")
#     response = await login_request(async_client, email, "WrongPassword")
#     assert_invalid_credentials_response(response)
#
#
# @pytest.mark.anyio
# async def test_login_locked_account(async_client: AsyncClient, create_user):
#     email = await create_user(is_locked=True, login_failed_count=5)
#     response = await login_request(async_client, email, "StrongPassword123")
#
#     assert response.status_code == 403
#     data = response.json()
#     assert "Account is temporarily locked" in data["message"]
#
#
# @pytest.mark.anyio
# async def test_login_nonexistent_user(async_client: AsyncClient):
#     response = await login_request(async_client, "nonexistent@example.com", "any_password")
#     assert_invalid_credentials_response(response)
#
#
# @pytest.mark.anyio
# async def test_login_password_expired(login_user):
#     user = await login_user(password_expired=True)
#     assert user["password_expired"] is True
#     assert user["access_token"]
#
#
# @pytest.mark.anyio
# async def test_login_password_validity_none(async_client: AsyncClient, create_user):
#     email = await create_user()
#     await database.execute(
#         users_table.update()
#         .where(users_table.c.user_email == email)
#         .values(password_validity_date=None)
#     )
#
#     response = await login_request(async_client, email, "StrongPassword123")
#
#     assert response.status_code == 200
#     assert response.json()["password_expired"] is False
#
#
# @pytest.mark.anyio
# async def test_login_exactly_max_failed_attempts(async_client: AsyncClient, create_user):
#     email = await create_user(login_failed_count=5)
#     response = await login_request(async_client, email, "WrongPassword123")
#
#     assert response.status_code == 403
#     assert "Account locked due to multiple failed login attempts" in response.json()["message"]
