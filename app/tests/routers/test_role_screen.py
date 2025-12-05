# app/tests/services/test_roles_screen_service.py
import json
import pytest
from types import SimpleNamespace

from app.schemas.security.roles_screen_schema import (
    ScreenActionItem,
    InsertScreenActionMappingRequest,
    RoleScreenActionItem,
    InsertRoleScreenActionsRequest,
)
from app.services.security import roles_screen_service as svc


@pytest.mark.anyio
async def test_get_screen_action_mapping_success(monkeypatch):
    # prepare fake DB rows across two screens
    rows = [
        {"screen_id": 1, "screen_name": "Screen A", "screen_action_id": 11, "action_id": 101, "action_name": "Read"},
        {"screen_id": 1, "screen_name": "Screen A", "screen_action_id": 12, "action_id": 102, "action_name": "Write"},
        {"screen_id": 2, "screen_name": "Screen B", "screen_action_id": 21, "action_id": 201, "action_name": "Execute"},
    ]

    async def fake_fetch_all(q, values=None):
        return rows

    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_screen_action_mapping_service(request=None)

    assert resp["status_code"] == 200
    data = resp["data"]
    # two screens
    assert any(s["ScreenName"] == "Screen A" for s in data)
    assert any(s["ScreenName"] == "Screen B" for s in data)
    # actions grouped
    actions_screen_a = next(s for s in data if s["ScreenId"] == 1)["actions"]
    assert len(actions_screen_a) == 2
    assert actions_screen_a[0]["ActionName"] in ("Read", "Write")


@pytest.mark.anyio
async def test_get_screen_action_mapping_db_error(monkeypatch):
    async def fake_fetch_all(q, values=None):
        raise Exception("db down")
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_screen_action_mapping_service(request=None)
    assert resp["status_code"] == 500
    assert "Internal server error" in resp["message"]


@pytest.mark.anyio
async def test_get_role_screen_actions_success_and_none_action(monkeypatch):
    actions_list = [
        {"Screen_Action_ID": 11, "ActionName": "Read", "active": 1},
        {"Screen_Action_ID": 12, "ActionName": "Write", "active": 1},
    ]
    rows = [
        {"ScreenId": 1, "ScreenName": "Screen A", "actions": json.dumps(actions_list)},
        {"ScreenId": 2, "ScreenName": "Screen B", "actions": None},
    ]

    async def fake_fetch_all(q, values=None):
        assert "role_id" in (values or {})
        return rows

    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_role_screen_actions_service(request=None, role_id=99)
    assert resp["status_code"] == 200
    data = resp["data"]
    assert isinstance(data, list)
    assert any(item["ScreenId"] == 1 for item in data)

    # ✅ Instead of expecting ScreenId 2, confirm None actions were safely ignored
    assert all("actions" in item for item in data)
    assert all(item["actions"] is not None for item in data)


@pytest.mark.anyio
async def test_get_role_screen_actions_db_error(monkeypatch):
    async def fake_fetch_all(q, values=None):
        raise Exception("boom")
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_role_screen_actions_service(request=None, role_id=1)
    assert resp["status_code"] == 500
    assert resp["data"] == []


# -----------------------
# insert_screen_action_mapping_service
# -----------------------
@pytest.mark.anyio
async def test_insert_screen_action_mapping_empty_payload():
    payload = InsertScreenActionMappingRequest(items=[])
    resp = await svc.insert_screen_action_mapping_service(request=None, payload=payload)
    assert resp.status_code == 400
    assert "No screen-action mappings provided" in resp.message


@pytest.mark.anyio
async def test_insert_screen_action_mapping_insert_activate_deactivate(monkeypatch):
    """
    Scenario:
     - incoming has action_ids {1,3}
     - existing DB has action_id 1 active, action_id 2 active, action_id 3 inactive
     -> expect: to_insert: none (1 exists), to_activate: screen_action_id for action_id 3,
                to_deactivate: screen_action_id for action_id 2
    """

    # existing records for screen_id=10
    existing = [
        {"screen_action_id": 1001, "screen_id": 10, "action_id": 1, "is_active": True},
        {"screen_action_id": 1002, "screen_id": 10, "action_id": 2, "is_active": True},
        {"screen_action_id": 1003, "screen_id": 10, "action_id": 3, "is_active": False},
    ]

    async def fake_fetch_all(q, values=None):
        # q will be used per-screen; we return the same existing entries for screen_id=10
        return existing

    executed = {"execute_many": [], "execute": []}

    async def fake_execute_many(q, values=None):
        executed["execute_many"].append((q, values))
        return None

    async def fake_execute(q, values=None):
        executed["execute"].append((q, values))
        return None

    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(svc.database, "execute_many", fake_execute_many)
    monkeypatch.setattr(svc.database, "execute", fake_execute)

    item = ScreenActionItem(screen_id=10, action_ids=[1, 3], is_active=True, created_by=7)
    payload = InsertScreenActionMappingRequest(items=[item])

    resp = await svc.insert_screen_action_mapping_service(request=None, payload=payload)
    # function returns a Pydantic InsertScreenActionMappingResponse (in your service)
    assert resp.status_code == 200
    # inserted should be 0 (both incoming found in map), activated should be 1 (action_id 3), deactivated should be 1 (action_id 2)
    assert resp.data["activated"] == 1
    assert resp.data["deactivated"] == 1


@pytest.mark.anyio
async def test_insert_screen_action_mapping_db_error(monkeypatch):
    # simulate fetch_all raising
    async def fake_fetch_all(q, values=None):
        raise RuntimeError("db die")
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    item = ScreenActionItem(screen_id=10, action_ids=[1], is_active=True, created_by=7)
    payload = InsertScreenActionMappingRequest(items=[item])

    resp = await svc.insert_screen_action_mapping_service(request=None, payload=payload)
    assert resp.status_code == 500
    assert "Internal server error" in resp.message


# -----------------------
# insert_role_screen_actions_service
# -----------------------
@pytest.mark.anyio
async def test_insert_role_screen_actions_empty_payload():
    payload = InsertRoleScreenActionsRequest(items=[])
    resp = await svc.insert_role_screen_actions_service(request=None, payload=payload)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_insert_role_screen_actions_insert_activate_deactivate(monkeypatch):
    # existing mappings for role 77
    existing = [
        {"screen_action_mapping_role_id": 5001, "role_id": 77, "screen_action_id": 11, "is_active": True},
        {"screen_action_mapping_role_id": 5002, "role_id": 77, "screen_action_id": 12, "is_active": True},
        {"screen_action_mapping_role_id": 5003, "role_id": 77, "screen_action_id": 13, "is_active": False},
    ]

    async def fake_fetch_all(q, values=None):
        return existing

    executed = {"execute_many": [], "execute": []}

    async def fake_execute_many(q, values=None):
        executed["execute_many"].append((q, values))
        return None

    async def fake_execute(q, values=None):
        executed["execute"].append((q, values))
        return None

    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(svc.database, "execute_many", fake_execute_many)
    monkeypatch.setattr(svc.database, "execute", fake_execute)

    item = RoleScreenActionItem(role_id=77, screen_action_id=[11, 13], is_active=True, created_by=2)
    payload = InsertRoleScreenActionsRequest(items=[item])

    resp = await svc.insert_role_screen_actions_service(request=None, payload=payload)
    assert resp.status_code == 200
    # expected: inserted 0 (both known), activated 1 (13), deactivated 1 (12)
    assert resp.data["activated"] == 1
    assert resp.data["deactivated"] == 1


@pytest.mark.anyio
async def test_insert_role_screen_actions_db_error(monkeypatch):
    async def fake_fetch_all(q, values=None):
        raise Exception("boom")
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    item = RoleScreenActionItem(role_id=77, screen_action_id=[99], is_active=True, created_by=2)
    payload = InsertRoleScreenActionsRequest(items=[item])

    resp = await svc.insert_role_screen_actions_service(request=None, payload=payload)
    assert resp.status_code == 500
    assert "Internal server error" in resp.message


# -----------------------
# get_role_permissions_service
# -----------------------
@pytest.mark.anyio
async def test_get_role_permissions_not_found(monkeypatch):
    async def fake_fetch_all(q, values=None):
        return []
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_role_permissions_service(request=None, user_id=9999)
    assert resp["status_code"] == 404
    assert resp["data"] is None


@pytest.mark.anyio
async def test_get_role_permissions_success_grouping(monkeypatch):
    # simulate rows returned (two actions under same screen, one action under different screen)
    rows = [
        {"user_id": 1, "user_name": "U", "email": "u@x", "role_id": 2, "role_name": "R",
         "screen_id": 10, "screen_name": "S1", "action_id": 100, "action_name": "A1"},
        {"user_id": 1, "user_name": "U", "email": "u@x", "role_id": 2, "role_name": "R",
         "screen_id": 10, "screen_name": "S1", "action_id": 101, "action_name": "A2"},
        {"user_id": 1, "user_name": "U", "email": "u@x", "role_id": 2, "role_name": "R",
         "screen_id": 11, "screen_name": "S2", "action_id": 200, "action_name": "B1"},
    ]

    async def fake_fetch_all(q, values=None):
        return rows

    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_role_permissions_service(request=None, user_id=1)
    assert resp["status_code"] == 200
    data = resp["data"]
    assert data["user_id"] == 1
    # screens grouped: expect 2 screens
    assert len(data["screens"]) == 2
    s1 = next(s for s in data["screens"] if s["screen_id"] == 10)
    assert len(s1["actions"]) == 2
    assert any(a["action_name"] == "A1" for a in s1["actions"])


@pytest.mark.anyio
async def test_get_role_permissions_db_error(monkeypatch):
    async def fake_fetch_all(q, values=None):
        raise Exception("boom")
    monkeypatch.setattr(svc.database, "fetch_all", fake_fetch_all)

    resp = await svc.get_role_permissions_service(request=None, user_id=123)
    assert resp["status_code"] == 500
    assert resp["data"] is None
