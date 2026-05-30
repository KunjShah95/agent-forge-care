import pytest
import uuid
from unittest.mock import AsyncMock

from tests.conftest import (
    MockResult,
    make_alert_config,
    make_memory_entry,
    setup_mock_execute,
    TEST_USER_ID,
    _uid,
)


@pytest.mark.asyncio
async def test_list_alert_configs(auth_client, mock_db):
    alert = make_alert_config()
    count_result = MockResult(scalar_value=1)
    alerts_result = MockResult(scalars_list=[alert])

    mock_db.execute = AsyncMock(side_effect=[count_result, alerts_result])

    response = await auth_client.get("/api/v1/monitor/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Test Alert"


@pytest.mark.asyncio
async def test_list_alert_configs_empty(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    alerts_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, alerts_result])

    response = await auth_client.get("/api/v1/monitor/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_alert_configs_pagination(auth_client, mock_db):
    count_result = MockResult(scalar_value=20)
    alerts_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, alerts_result])

    response = await auth_client.get("/api/v1/monitor/alerts?page=2&limit=5")
    assert response.status_code == 200
    assert response.json()["page"] == 2


@pytest.mark.asyncio
async def test_list_alert_configs_no_auth(async_client):
    response = await async_client.get("/api/v1/monitor/alerts")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_alert_config_success(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/monitor/alerts",
        json={
            "name": "ML Internships",
            "keywords": ["machine learning", "AI"],
            "locations": ["San Francisco", "Remote"],
            "opportunity_types": ["Internship"],
            "min_match_score": 85,
            "frequency": "daily",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "ML Internships"
    assert data["min_match_score"] == 85
    assert data["is_active"] is True
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_alert_config_defaults(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/monitor/alerts",
        json={"name": "Simple Alert"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["min_match_score"] == 80
    assert data["frequency"] == "daily"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_alert_config_missing_name(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/monitor/alerts",
        json={"keywords": ["python"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_config_no_auth(async_client):
    response = await async_client.post(
        "/api/v1/monitor/alerts",
        json={"name": "Test"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_alert_config_success(auth_client, mock_db):
    alert = make_alert_config()
    setup_mock_execute(mock_db, [MockResult(scalar_value=alert)])

    response = await auth_client.patch(
        f"/api/v1/monitor/alerts/{alert.id}",
        json={"name": "Updated Alert", "min_match_score": 90},
    )
    assert response.status_code == 200
    assert alert.name == "Updated Alert"
    assert alert.min_match_score == 90


@pytest.mark.asyncio
async def test_update_alert_config_toggle_active(auth_client, mock_db):
    alert = make_alert_config(is_active=True)
    setup_mock_execute(mock_db, [MockResult(scalar_value=alert)])

    response = await auth_client.patch(
        f"/api/v1/monitor/alerts/{alert.id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert alert.is_active is False


@pytest.mark.asyncio
async def test_update_alert_config_keywords(auth_client, mock_db):
    alert = make_alert_config()
    setup_mock_execute(mock_db, [MockResult(scalar_value=alert)])

    response = await auth_client.patch(
        f"/api/v1/monitor/alerts/{alert.id}",
        json={"keywords": ["rust", "go", "kubernetes"]},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_alert_config_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.patch(
        f"/api/v1/monitor/alerts/{_uid()}",
        json={"name": "Not Found"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_alert_config_success(auth_client, mock_db):
    alert = make_alert_config()
    setup_mock_execute(mock_db, [MockResult(scalar_value=alert)])

    response = await auth_client.delete(f"/api/v1/monitor/alerts/{alert.id}")
    assert response.status_code == 204
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_alert_config_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.delete(f"/api/v1/monitor/alerts/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_alert_config_no_auth(async_client):
    response = await async_client.delete(f"/api/v1/monitor/alerts/{_uid()}")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_monitor_settings_create(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.patch(
        "/api/v1/monitor/settings",
        json={
            "keywords": ["python", "ml"],
            "locations": ["Remote"],
            "frequency": "weekly",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_monitor_settings_existing(auth_client, mock_db):
    entry = make_memory_entry(key="monitor_settings", value={})
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])

    response = await auth_client.patch(
        "/api/v1/monitor/settings",
        json={"keywords": ["rust"], "max_results": 50},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


@pytest.mark.asyncio
async def test_update_monitor_settings_no_auth(async_client):
    response = await async_client.patch(
        "/api/v1/monitor/settings",
        json={"keywords": ["test"]},
    )
    assert response.status_code in (401, 403)
