import pytest
import uuid
from unittest.mock import AsyncMock, patch

from tests.conftest import (
    MockResult,
    make_opportunity,
    make_match_score,
    setup_mock_execute,
    TEST_USER_ID,
    OTHER_USER_ID,
    _uid,
)
from app.models.user import Opportunity


@pytest.mark.asyncio
async def test_list_opportunities(auth_client, mock_db):
    opp = make_opportunity()
    count_result = MockResult(scalar_value=1)
    opp_result = MockResult(scalars_list=[opp])
    ms_result = MockResult(scalar_value=None)

    mock_db.execute = AsyncMock(side_effect=[count_result, opp_result, ms_result])

    response = await auth_client.get("/api/v1/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "ML Research Intern"


@pytest.mark.asyncio
async def test_list_opportunities_empty(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    opp_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, opp_result])

    response = await auth_client.get("/api/v1/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_opportunities_with_filters(auth_client, mock_db):
    opp = make_opportunity(remote=True)
    count_result = MockResult(scalar_value=1)
    opp_result = MockResult(scalars_list=[opp])
    ms_result = MockResult(scalar_value=None)

    mock_db.execute = AsyncMock(side_effect=[count_result, opp_result, ms_result])

    response = await auth_client.get(
        "/api/v1/opportunities?type=Internship&remote=true&search=ML"
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_opportunities_pagination(auth_client, mock_db):
    count_result = MockResult(scalar_value=50)
    opp_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, opp_result])

    response = await auth_client.get("/api/v1/opportunities?page=2&limit=10")
    assert response.status_code == 200
    assert response.json()["page"] == 2


@pytest.mark.asyncio
async def test_list_opportunities_with_match_score(auth_client, mock_db):
    opp = make_opportunity()
    ms = make_match_score(opp_id=opp.id)
    count_result = MockResult(scalar_value=1)
    opp_result = MockResult(scalars_list=[opp])
    ms_result = MockResult(scalars_list=[ms])

    mock_db.execute = AsyncMock(side_effect=[count_result, opp_result, ms_result])

    response = await auth_client.get("/api/v1/opportunities")
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["match_score"] == 85.5
    assert "Strong skill match" in data["items"][0]["match_reasons"]


@pytest.mark.asyncio
async def test_list_opportunities_no_auth(async_client):
    response = await async_client.get("/api/v1/opportunities")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_opportunity_success(auth_client, mock_db):
    opp = make_opportunity()
    opp_result = MockResult(scalar_value=opp)
    ms_result = MockResult(scalar_value=None)

    mock_db.execute = AsyncMock(side_effect=[opp_result, ms_result])

    response = await auth_client.get(f"/api/v1/opportunities/{opp.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "ML Research Intern"


@pytest.mark.asyncio
async def test_get_opportunity_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.get(f"/api/v1/opportunities/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_opportunity_with_match(auth_client, mock_db):
    opp = make_opportunity()
    ms = make_match_score(opp_id=opp.id)
    opp_result = MockResult(scalar_value=opp)
    ms_result = MockResult(scalar_value=ms)

    mock_db.execute = AsyncMock(side_effect=[opp_result, ms_result])

    response = await auth_client.get(f"/api/v1/opportunities/{opp.id}")
    assert response.status_code == 200
    assert response.json()["match_score"] == 85.5


@pytest.mark.asyncio
async def test_matched_opportunities(auth_client, mock_db):
    opp = make_opportunity()
    ms = make_match_score(opp_id=opp.id)

    mock_row = (opp, ms)
    mock_result = MockResult(scalars_list=[mock_row])
    mock_result.all = lambda: [mock_row]
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/opportunities/matches")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["match_score"] == 85.5


@pytest.mark.asyncio
async def test_matched_opportunities_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_result.all = lambda: []
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/opportunities/matches")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
@patch("app.agents.graph.run_opportunity_scan", new_callable=AsyncMock)
async def test_refresh_opportunities(mock_scan, auth_client, mock_db):
    mock_scan.return_value = str(uuid.uuid4())

    response = await auth_client.post("/api/v1/opportunities/refresh")
    assert response.status_code == 202
    assert "task_id" in response.json()
    mock_scan.assert_called_once()


@pytest.mark.asyncio
async def test_list_opportunities_invalid_page(auth_client, mock_db):
    response = await auth_client.get("/api/v1/opportunities?page=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_opportunities_invalid_limit(auth_client, mock_db):
    response = await auth_client.get("/api/v1/opportunities?limit=200")
    assert response.status_code == 422
