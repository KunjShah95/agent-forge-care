import pytest
from datetime import datetime, timezone
from tests.conftest import (
    MockResult,
    make_memory_entry,
    setup_mock_execute,
)


@pytest.mark.asyncio
async def test_list_notifications_empty(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalars_list=[])])
    resp = await auth_client.get("/api/v1/notifications")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_list_notifications_returns_items(auth_client, mock_db):
    entry1 = make_memory_entry(
        key="notification:alert",
        value={"title": "New Match", "body": "You have a match", "type": "alert", "read": False},
    )
    entry2 = make_memory_entry(
        key="notification:info",
        value={"title": "Welcome", "body": "Welcome!", "type": "info", "read": True},
    )
    setup_mock_execute(mock_db, [MockResult(scalars_list=[entry1, entry2])])
    resp = await auth_client.get("/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "New Match"
    assert data["items"][0]["read"] is False
    assert data["items"][1]["title"] == "Welcome"
    assert data["items"][1]["read"] is True


@pytest.mark.asyncio
async def test_list_notifications_default_values(auth_client, mock_db):
    entry = make_memory_entry(key="notification:x", value={})
    setup_mock_execute(mock_db, [MockResult(scalars_list=[entry])])
    resp = await auth_client.get("/api/v1/notifications")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["title"] == ""
    assert item["body"] == ""
    assert item["type"] == "info"
    assert item["read"] is False


@pytest.mark.asyncio
async def test_list_notifications_null_value(auth_client, mock_db):
    entry = make_memory_entry(key="notification:x", value=None)
    setup_mock_execute(mock_db, [MockResult(scalars_list=[entry])])
    resp = await auth_client.get("/api/v1/notifications")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


@pytest.mark.asyncio
async def test_mark_notification_read(auth_client, mock_db):
    entry = make_memory_entry(
        key="notification:test",
        value={"title": "Test", "body": "Body", "type": "alert", "read": False},
    )
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])
    resp = await auth_client.patch(f"/api/v1/notifications/{entry.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["read"] is True
    assert data["title"] == "Test"
    assert entry.value["read"] is True


@pytest.mark.asyncio
async def test_mark_notification_read_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])
    resp = await auth_client.patch("/api/v1/notifications/nonexistent-id")
    assert resp.status_code == 404
    assert "Notification not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_mark_notification_read_null_value(auth_client, mock_db):
    entry = make_memory_entry(key="notification:test", value=None)
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])
    resp = await auth_client.patch(f"/api/v1/notifications/{entry.id}")
    assert resp.status_code == 200
    assert resp.json()["read"] is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read(auth_client, mock_db):
    entry1 = make_memory_entry(
        key="notification:a",
        value={"title": "A", "body": "", "type": "info", "read": False},
    )
    entry2 = make_memory_entry(
        key="notification:b",
        value={"title": "B", "body": "", "type": "info", "read": False},
    )
    setup_mock_execute(mock_db, [MockResult(scalars_list=[entry1, entry2])])
    resp = await auth_client.post("/api/v1/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert entry1.value["read"] is True
    assert entry2.value["read"] is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read_empty(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalars_list=[])])
    resp = await auth_client.post("/api/v1/notifications/read-all")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_list_notifications_requires_auth(async_client):
    resp = await async_client.get("/api/v1/notifications")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mark_notification_read_requires_auth(async_client):
    resp = await async_client.patch("/api/v1/notifications/some-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mark_all_read_requires_auth(async_client):
    resp = await async_client.post("/api/v1/notifications/read-all")
    assert resp.status_code == 401
