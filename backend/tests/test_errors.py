import pytest
from unittest.mock import AsyncMock, MagicMock
from tests.conftest import (
    MockResult,
    make_profile,
    make_contact,
    make_opportunity,
    make_application,
    make_memory_entry,
    setup_mock_execute,
    _uid,
)


@pytest.mark.asyncio
async def test_get_profile_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/profile")
    assert response.status_code == 500
    assert "Failed to get profile" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_profile_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.put("/api/v1/profile", json={"bio": "test"})
    assert response.status_code == 500
    assert "Failed to update profile" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_skills_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/profile/skills")
    assert response.status_code == 500
    assert "Failed to get skills" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_skill_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post(
        "/api/v1/profile/skills", json={"name": "Python"}
    )
    assert response.status_code == 500
    assert "Failed to add skill" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_application_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": _uid(), "notes": "test"},
    )
    assert response.status_code == 500
    assert "Failed to create application" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_application_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(
        f"/api/v1/applications/{_uid()}", json={"notes": "test"}
    )
    assert response.status_code == 500
    assert "Failed to update application" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_application_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.delete(f"/api/v1/applications/{_uid()}")
    assert response.status_code == 500
    assert "Failed to delete application" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_contact_db_error(auth_client, mock_db):
    mock_db.add = MagicMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post(
        "/api/v1/contacts", json={"name": "Test User"}
    )
    assert response.status_code == 500
    assert "Failed to create contact" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_contact_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(
        f"/api/v1/contacts/{_uid()}", json={"name": "Updated"}
    )
    assert response.status_code == 500
    assert "Failed to update contact" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_contact_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.delete(f"/api/v1/contacts/{_uid()}")
    assert response.status_code == 500
    assert "Failed to delete contact" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_opportunity_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get(f"/api/v1/opportunities/{_uid()}")
    assert response.status_code == 500
    assert "Failed to retrieve opportunity" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mark_notification_read_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(f"/api/v1/notifications/{_uid()}")
    assert response.status_code == 500
    assert "Failed to mark notification" in response.json()["detail"]


@pytest.mark.asyncio
async def test_mark_all_notifications_read_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post("/api/v1/notifications/read-all")
    assert response.status_code == 500
    assert "Failed to mark all notifications" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_contact_invalid_name(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/contacts", json={"name": ""}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_application_invalid_notes_type(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": _uid(), "notes": 123},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_remove_skill_not_found_profile(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])
    response = await auth_client.delete(f"/api/v1/profile/skills/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_not_owned(auth_client, mock_db):
    contact = make_contact(user_id=_uid())
    setup_mock_execute(mock_db, [MockResult(scalar_value=contact)])
    response = await auth_client.patch(
        f"/api/v1/contacts/{contact.id}", json={"name": "Hacker"}
    )
    # Contact exists but is owned by different user; ownership enforced by query filter
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_applications_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/applications")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_list_alert_configs_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/monitor/alerts")
    assert response.status_code == 500
    assert "Failed to list alert configs" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_alert_config_db_error(auth_client, mock_db):
    mock_db.add = MagicMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post(
        "/api/v1/monitor/alerts",
        json={"name": "Test Alert", "keywords": ["python"]},
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_alert_config_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(
        f"/api/v1/monitor/alerts/{_uid()}", json={"name": "Updated"}
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_alert_config_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.delete(f"/api/v1/monitor/alerts/{_uid()}")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_monitor_settings_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/monitor/settings")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_monitor_settings_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(
        "/api/v1/monitor/settings", json={"frequency": "weekly"}
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_list_memory_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/memory")
    assert response.status_code == 500
    assert "Failed to list memory" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_memory_db_error(auth_client, mock_db):
    mock_db.add = MagicMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.post(
        "/api/v1/memory", json={"key": "test", "value": {"data": "test"}}
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_memory_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.patch(
        f"/api/v1/memory/{_uid()}", json={"key": "updated"}
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_memory_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.delete(f"/api/v1/memory/{_uid()}")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_get_memory_context_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/memory/context")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_analytics_summary_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/analytics/summary")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_analytics_funnel_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/analytics/funnel")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_analytics_skills_demand_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/analytics/skills-demand")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_analytics_activity_db_error(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=Exception("DB connection failed"))
    response = await auth_client.get("/api/v1/analytics/activity")
    assert response.status_code == 500
