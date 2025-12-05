# import uuid
# import pytest
# from httpx import AsyncClient
# from app.config import config
#
# @pytest.mark.anyio
# async def test_register_single_user_success(async_client: AsyncClient):
#     payload = {
#         "users": {
#             "user_first_name": "John",
#             "user_middle_name": "A",
#             "user_last_name": "Doe",
#             "user_email": "john.doe.test@example.com",
#             "user_phone": "1234567890",
#             "user_address": "123 Main St",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#
#     response = await async_client.post("/users/registeruser", json=payload)
#     data = response.json()
#
#     assert response.status_code == 201
#     assert data["status"] == "success"
#     assert "created_user_ids" in data["data"]
#     assert len(data["data"]["created_user_ids"]) == 1
#
#
# @pytest.mark.anyio
# async def test_register_multiple_users_success(async_client: AsyncClient):
#     payload = {
#         "users": [
#             {
#                 "user_first_name": "Alice",
#                 "user_middle_name": "B",
#                 "user_last_name": "Smith",
#                 "user_email": "alice.smith.test@example.com",
#                 "user_phone": "1112223333",
#                 "user_address": "456 Elm St",
#                 "role_id": 2
#             },
#             {
#                 "user_first_name": "Bob",
#                 "user_middle_name": "C",
#                 "user_last_name": "Brown",
#                 "user_email": "bob.brown.test@example.com",
#                 "user_phone": "2223334444",
#                 "user_address": "789 Pine St",
#                 "role_id": 2
#             }
#         ],
#         "created_by": 1,
#         "is_active": True
#     }
#
#     response = await async_client.post("/users/registeruser", json=payload)
#     data = response.json()
#
#     assert response.status_code == 201
#     assert data["status"] == "success"
#     assert "created_user_ids" in data["data"]
#     assert len(data["data"]["created_user_ids"]) == 2
#
#
# @pytest.mark.anyio
# async def test_register_duplicate_user(async_client: AsyncClient):
#     # First registration
#     payload = {
#         "users": {
#             "user_first_name": "Jane",
#             "user_middle_name": "X",
#             "user_last_name": "Doe",
#             "user_email": "jane.dup@example.com",
#             "user_password": "Passw0rd!",
#             "user_phone": "0000000000",
#             "user_address": "Somewhere",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     await async_client.post("/users/registeruser", json=payload)
#
#     # Duplicate registration
#     response = await async_client.post("/users/registeruser", json=payload)
#     data = response.json()
#
#     assert response.status_code == 409
#     assert len(data["data"]["created_user_ids"]) == 0
#     assert len(data["data"]["existing_users"]) == 1
#     assert data["data"]["existing_users"][0]["user_email"] == "jane.dup@example.com"
#
#
# @pytest.mark.anyio
# async def test_register_user_missing_fields(async_client: AsyncClient):
#     payload = {
#         "users": {
#             # Missing user_email and user_first_name
#             "user_last_name": "Incomplete",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#
#     response = await async_client.post("/users/registeruser", json=payload)
#     assert response.status_code == 422  # Unprocessable Entity (validation error)
#
#
# @pytest.mark.anyio
# async def test_get_users_all(async_client: AsyncClient):
#     response = await async_client.get("/users/getusers")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert "data" in data
#     assert isinstance(data["data"], list)
#
#
# @pytest.mark.anyio
# async def test_get_users_by_email(async_client: AsyncClient):
#     # Register a known user
#     email = "test.email@example.com"
#     payload = {
#         "users": {
#             "user_first_name": "Test",
#             "user_middle_name": "T",
#             "user_last_name": "User",
#             "user_email": email,
#             "user_password": "Test@1234",
#             "user_phone": "9876543210",
#             "user_address": "123 Test Blvd",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     await async_client.post("/users/registeruser", json=payload)
#
#     # Then retrieve it
#     response = await async_client.get(f"/users/getusers?user_email={email}")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert any(u["user_email"] == email for u in data["data"])
#
# @pytest.mark.anyio
# async def test_get_users_invalid_user_id(async_client: AsyncClient):
#     response = await async_client.get("/users/getusers?user_id=9999999")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert data["data"] == []
#
#
# @pytest.mark.anyio
# async def test_get_users_by_active_status(async_client: AsyncClient):
#     response = await async_client.get("/users/getusers?is_active=true")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert all(u["is_active"] is True for u in data["data"])
#
#
# @pytest.mark.anyio
# async def test_register_user_invalid_email(async_client: AsyncClient):
#     payload = {
#         "users": {
#             "user_first_name": "Invalid",
#             "user_middle_name": "I",
#             "user_last_name": "Email",
#             "user_email": "invalid-email",  # not a valid email
#             "user_phone": "1231231234",
#             "user_address": "Fake St",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     response = await async_client.post("/users/registeruser", json=payload)
#     assert response.status_code == 422  # validation error
#
# @pytest.mark.anyio
# async def test_register_user_invalid_role(async_client: AsyncClient):
#     payload = {
#         "users": {
#             "user_first_name": "Role",
#             "user_middle_name": "X",
#             "user_last_name": "Invalid",
#             "user_email": "invalid.role@example.com",
#             "user_phone": "9999999999",
#             "user_address": "Nowhere",
#             "role_id": 9999  # assume this doesn't exist
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#
#     response = await async_client.post("/users/registeruser", json=payload)
#
#     # Even though it inserts the user, the role mapping might silently fail.
#     # Add validation in your service layer if role_id should be validated.
#     # For now, check 201
#     assert response.status_code in [201, 422, 400]
#
# @pytest.mark.anyio
# async def test_delete_already_deleted_user(async_client: AsyncClient):
#     payload = {
#         "users": {
#             "user_first_name": "Already",
#             "user_middle_name": "Gone",
#             "user_last_name": "User",
#             "user_email": "already.deleted@example.com",
#             "user_phone": "5551234567",
#             "user_address": "Ghost Town",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#
#     # Create
#     await async_client.post("/users/registeruser", json=payload)
#     get_resp = await async_client.get("/users/getusers?user_email=already.deleted@example.com")
#     user_id = get_resp.json()["data"][0]["user_id"]
#
#     # Delete once
#     await async_client.delete(f"/users/deleteuser/{user_id}")
#
#     # Try deleting again
#     response = await async_client.delete(f"/users/deleteuser/{user_id}")
#     assert response.status_code == 409
#     assert response.json()["message"] == f"User {user_id} is already Deleted."
#
#
# @pytest.mark.anyio
# async def test_bulk_user_registration_with_duplicates(async_client: AsyncClient):
#     existing_email = "bulk.dup@example.com"
#     first_payload = {
#         "users": {
#             "user_first_name": "Bulk",
#             "user_middle_name": "A",
#             "user_last_name": "Dup",
#             "user_email": existing_email,
#             "user_phone": "1010101010",
#             "user_address": "Dup Lane",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     await async_client.post("/users/registeruser", json=first_payload)
#
#     # Try registering again with one duplicate and one new
#     second_payload = {
#         "users": [
#             first_payload["users"],
#             {
#                 "user_first_name": "New",
#                 "user_middle_name": "User",
#                 "user_last_name": "Ok",
#                 "user_email": "newuser.ok@example.com",
#                 "user_phone": "1111111111",
#                 "user_address": "Green St",
#                 "role_id": 1
#             }
#         ],
#         "created_by": 1,
#         "is_active": True
#     }
#
#     response = await async_client.post("/users/registeruser", json=second_payload)
#     assert response.status_code == 409
#     assert len(response.json()["data"]["created_user_ids"]) == 1
#     assert len(response.json()["data"]["existing_users"]) == 1
#
#
# @pytest.mark.anyio
# async def test_get_users_by_all_filters(async_client: AsyncClient):
#     email = "filtered.user@example.com"
#     payload = {
#         "users": {
#             "user_first_name": "Filter",
#             "user_middle_name": "U",
#             "user_last_name": "Match",
#             "user_email": email,
#             "user_phone": "9998887777",
#             "user_address": "Filter Street",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#
#     await async_client.post("/users/registeruser", json=payload)
#     get_resp = await async_client.get(f"/users/getusers?user_email={email}")
#     user_id = get_resp.json()["data"][0]["user_id"]
#
#     response = await async_client.get(f"/users/getusers?user_id={user_id}&user_email={email}&is_active=true")
#     data = response.json()
#
#     assert response.status_code == 200
#     assert len(data["data"]) == 1
#     assert data["data"][0]["user_email"] == email
#
#
# @pytest.mark.anyio
# async def test_get_users_no_match(async_client: AsyncClient):
#     response = await async_client.get("/users/getusers?user_email=nonexistent@example.com")
#     assert response.status_code == 200
#     assert response.json()["data"] == []
#
#
# @pytest.mark.anyio
# async def test_get_users_defaults_to_active_true(async_client: AsyncClient):
#     # Register a known user
#     payload = {
#         "users": {
#             "user_first_name": "Active",
#             "user_middle_name": "Test",
#             "user_last_name": "Fallback",
#             "user_email": f"active_{uuid.uuid4().hex[:8]}@example.com",
#             "user_phone": "7777777777",
#             "user_address": "Active City",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     await async_client.post("/users/registeruser", json=payload)
#
#     response = await async_client.get("/users/getusers")
#     assert response.status_code == 200
#     assert all(user["is_active"] for user in response.json()["data"])
#
# # ------------------------------------------------------new------------------------------
#
# @pytest.mark.anyio
# async def test_update_user_invalid_phone(async_client: AsyncClient):
#     # First create a user
#     create_payload = {
#         "users": {
#             "user_first_name": "Invalid",
#             "user_middle_name": "Phone",
#             "user_last_name": "User",
#             "user_email": f"invphone_{uuid.uuid4().hex[:8]}@example.com",
#             "user_phone": "9876543210",
#             "user_address": "Nowhere",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     create_response = await async_client.post("/users/registeruser", json=create_payload)
#     user_id = create_response.json()["data"]["created_user_ids"][0]
#
#     update_payload = {
#         "user_first_name": "NewName",
#         "user_phone": "abc1234567",  # Invalid phone
#         "updated_by": 1
#     }
#
#     response = await async_client.put(f"/users/updateuser/{user_id}", json=update_payload)
#     assert response.status_code == 400
#     assert response.json()["detail"] == "Invalid phone number format."
#
#
# @pytest.mark.anyio
# async def test_update_user_invalid_role(async_client: AsyncClient):
#     create_payload = {
#         "users": {
#             "user_first_name": "Role",
#             "user_middle_name": "Fail",
#             "user_last_name": "Update",
#             "user_email": f"rolefail_{uuid.uuid4().hex[:8]}@example.com",
#             "user_phone": "8888888888",
#             "user_address": "Fail Street",
#             "role_id": 1
#         },
#         "created_by": 1,
#         "is_active": True
#     }
#     create_response = await async_client.post("/users/registeruser", json=create_payload)
#     user_id = create_response.json()["data"]["created_user_ids"][0]
#
#     update_payload = {
#         "user_first_name": "NewRole",
#         "role_id": 99999,  # Assume invalid
#         "updated_by": 1
#     }
#
#     response = await async_client.put(f"/users/updateuser/{user_id}", json=update_payload)
#     assert response.status_code == 400
#     assert "Invalid role_id" in response.json()["detail"]
#
#
# @pytest.mark.anyio
# async def test_update_nonexistent_user(async_client: AsyncClient):
#     update_payload = {
#         "user_first_name": "Ghost",
#         "user_phone": "1234567890",
#         "updated_by": 1
#     }
#
#     response = await async_client.put("/users/updateuser/999999", json=update_payload)
#     assert response.status_code == 404
#     assert "not found" in response.json()["detail"]
#
#
# @pytest.mark.anyio
# async def test_delete_nonexistent_user(async_client: AsyncClient):
#     response = await async_client.delete("/users/deleteuser/999999")
#     assert response.status_code == 404
#     assert "not found" in response.json()["detail"]
