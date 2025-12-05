# import pytest
# from httpx import AsyncClient
# from datetime import datetime, UTC
# from app.db.database import database
# from app.db.transaction.users import users as users_table
# from app.db.transaction.user_password_history import user_password_history
# from app.security import get_password_hash
#
# # Dummy passwords for test cases (do not use in production)
# TEST_OLD_PASSWORD = "StrongPassword123"
# TEST_NEW_PASSWORD = "NewStrongPass1!"
# TEST_WEAK_PASSWORD = "123"
# TEST_MISMATCH_PASSWORD = "MismatchPass1!"
# TEST_REUSED_PASSWORD = "OldPassword1!"
# TEST_FAKE_PASSWORD = "Anything123"
# TEST_ANOTHER_PASSWORD = "AnotherPass1!"
# TEST_INVALID_OLD_PASSWORD = "WrongPassword!"
#
#
# @pytest.mark.anyio
# async def test_change_password_success(async_client: AsyncClient, login_user):
#     """
#     Test that a user can successfully change their password.
#     """
#     user = await login_user()
#     payload = {
#         "old_password": TEST_OLD_PASSWORD,
#         "new_password": TEST_NEW_PASSWORD,
#         "confirm_password": TEST_NEW_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json=payload
#     )
#
#     assert response.status_code == 200
#     assert "success" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_incorrect_old_password(async_client: AsyncClient, login_user):
#     """
#     Test that the API returns an error when the old password is incorrect.
#     """
#     user = await login_user()
#     payload = {
#         "old_password": TEST_INVALID_OLD_PASSWORD,
#         "new_password": TEST_NEW_PASSWORD,
#         "confirm_password": TEST_NEW_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json=payload
#     )
#
#     assert response.status_code == 400
#     assert "old password is incorrect" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_weak_new_password(async_client: AsyncClient, login_user):
#     """
#     Test that the API rejects weak new passwords.
#     """
#     user = await login_user()
#     payload = {
#         "old_password": TEST_OLD_PASSWORD,
#         "new_password": TEST_WEAK_PASSWORD,
#         "confirm_password": TEST_WEAK_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json=payload
#     )
#
#     assert response.status_code == 400
#     assert "password must be at least" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_mismatch(async_client: AsyncClient, login_user):
#     """
#     Test that the API returns an error when new and confirm passwords do not match.
#     """
#     user = await login_user()
#     payload = {
#         "old_password": TEST_OLD_PASSWORD,
#         "new_password": TEST_NEW_PASSWORD,
#         "confirm_password": TEST_MISMATCH_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json=payload
#     )
#
#     assert response.status_code == 400
#     assert "do not match" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_reuse(async_client: AsyncClient, login_user):
#     """
#     Test that the API prevents reusing a previously used password.
#     """
#     user = await login_user()
#
#     # Fetch the user's DB record
#     user_record = await database.fetch_one(
#         users_table.select().where(users_table.c.email == user["email"])
#     )
#
#     # Insert reused password into history
#     reused_hashed = get_password_hash(TEST_REUSED_PASSWORD)
#     await database.execute(user_password_history.insert().values(
#         user_id=user_record["user_id"],
#         old_password=reused_hashed,
#         password_changed_date=datetime.now(UTC)
#     ))
#
#     payload = {
#         "old_password": TEST_OLD_PASSWORD,
#         "new_password": TEST_REUSED_PASSWORD,
#         "confirm_password": TEST_REUSED_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json=payload
#     )
#
#     assert response.status_code == 400
#     assert "reuse" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_user_not_found(async_client: AsyncClient):
#     """
#     Test that the API returns an error for an invalid/fake user token.
#     """
#     fake_token = "faketoken.invalid.jwt"
#     payload = {
#         "old_password": TEST_FAKE_PASSWORD,
#         "new_password": TEST_ANOTHER_PASSWORD,
#         "confirm_password": TEST_ANOTHER_PASSWORD,
#     }
#
#     response = await async_client.post(
#         f"/change-password?token={fake_token}",
#         json=payload
#     )
#
#     assert response.status_code in [401, 404]
#     assert "could not validate credentials" in response.json()["detail"].lower()
#
#
# @pytest.mark.anyio
# async def test_change_password_missing_fields(async_client: AsyncClient, login_user):
#     """
#     Test that the API returns a validation error when required fields are missing.
#     """
#     user = await login_user()
#
#     response = await async_client.post(
#         f"/change-password?token={user['access_token']}",
#         json={}  # Missing required fields
#     )
#
#     assert response.status_code == 422  # Unprocessable Entity (validation error)
