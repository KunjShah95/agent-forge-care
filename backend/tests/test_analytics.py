import pytest
from unittest.mock import AsyncMock

from tests.conftest import MockResult


@pytest.mark.asyncio
async def test_analytics_summary(auth_client, mock_db):
    matches_result = MockResult(scalar_value=5)
    apps_result = MockResult(scalar_value=20)
    interviews_result = MockResult(scalar_value=4)
    deadlines_result = MockResult(scalar_value=3)

    mock_db.execute = AsyncMock(
        side_effect=[matches_result, apps_result, interviews_result, deadlines_result]
    )

    response = await auth_client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["active_matches"] == 5
    assert data["applications"] == 20
    assert data["interview_rate"] == 20.0
    assert data["deadlines"] == 3


@pytest.mark.asyncio
async def test_analytics_summary_no_data(auth_client, mock_db):
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(scalar_value=0),
            MockResult(scalar_value=0),
            MockResult(scalar_value=0),
            MockResult(scalar_value=0),
        ]
    )

    response = await auth_client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["active_matches"] == 0
    assert data["applications"] == 0
    assert data["interview_rate"] == 0
    assert data["deadlines"] == 0


@pytest.mark.asyncio
async def test_analytics_summary_no_auth(async_client):
    response = await async_client.get("/api/v1/analytics/summary")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_analytics_funnel(auth_client, mock_db):
    mock_db.execute = AsyncMock(
        side_effect=[
            MockResult(scalar_value=10),
            MockResult(scalar_value=8),
            MockResult(scalar_value=5),
            MockResult(scalar_value=3),
            MockResult(scalar_value=1),
        ]
    )

    response = await auth_client.get("/api/v1/analytics/funnel")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["name"] == "Saved"
    assert data[0]["value"] == 10
    assert data[1]["name"] == "Applied"
    assert data[2]["name"] == "Oa"
    assert data[3]["name"] == "Interview"
    assert data[4]["name"] == "Offer"


@pytest.mark.asyncio
async def test_analytics_funnel_empty(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=[MockResult(scalar_value=0)] * 5)

    response = await auth_client.get("/api/v1/analytics/funnel")
    assert response.status_code == 200
    data = response.json()
    assert all(point["value"] == 0 for point in data)


@pytest.mark.asyncio
async def test_analytics_funnel_no_auth(async_client):
    response = await async_client.get("/api/v1/analytics/funnel")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_analytics_skills_demand(auth_client, mock_db):
    mock_result = MockResult(
        scalars_list=[
            ["Python", "PyTorch", "React"],
            ["Python", "TensorFlow"],
            ["Python", "React", "Docker"],
        ]
    )
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/analytics/skills-demand")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["skill"] == "Python"
    assert data[0]["demand"] == 100.0


@pytest.mark.asyncio
async def test_analytics_skills_demand_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/analytics/skills-demand")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_analytics_skills_demand_no_auth(async_client):
    response = await async_client.get("/api/v1/analytics/skills-demand")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_analytics_activity(auth_client, mock_db):
    mock_db.execute = AsyncMock(
        side_effect=[MockResult(scalar_value=i) for i in range(7)]
    )

    response = await auth_client.get("/api/v1/analytics/activity")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7
    for point in data:
        assert "day" in point
        assert "applications" in point
        assert "interviews" in point


@pytest.mark.asyncio
async def test_analytics_activity_no_data(auth_client, mock_db):
    mock_db.execute = AsyncMock(side_effect=[MockResult(scalar_value=0)] * 7)

    response = await auth_client.get("/api/v1/analytics/activity")
    assert response.status_code == 200
    data = response.json()
    assert all(p["applications"] == 0 for p in data)


@pytest.mark.asyncio
async def test_analytics_activity_no_auth(async_client):
    response = await async_client.get("/api/v1/analytics/activity")
    assert response.status_code in (401, 403)
