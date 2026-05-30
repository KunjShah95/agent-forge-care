import pytest
import uuid
from datetime import date
from unittest.mock import AsyncMock

from tests.conftest import (
    MockResult,
    make_application,
    make_opportunity,
    setup_mock_execute,
    TEST_USER_ID,
    OTHER_USER_ID,
    _uid,
)
from app.models.user import ApplicationStage


@pytest.mark.asyncio
async def test_list_applications(auth_client, mock_db):
    app_obj = make_application()
    opp = make_opportunity()

    count_result = MockResult(scalar_value=1)
    app_result = MockResult(scalars_list=[app_obj])
    opp_result = MockResult(scalar_value=opp)

    mock_db.execute = AsyncMock(side_effect=[count_result, app_result, opp_result])

    response = await auth_client.get("/api/v1/applications")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1


@pytest.mark.asyncio
async def test_list_applications_empty(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    app_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, app_result])

    response = await auth_client.get("/api/v1/applications")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_applications_pagination(auth_client, mock_db):
    count_result = MockResult(scalar_value=50)
    app_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, app_result])

    response = await auth_client.get("/api/v1/applications?page=3&limit=10")
    assert response.status_code == 200
    assert response.json()["page"] == 3


@pytest.mark.asyncio
async def test_list_applications_no_auth(async_client):
    response = await async_client.get("/api/v1/applications")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_application_success(auth_client, mock_db):
    opp = make_opportunity()
    opp_result = MockResult(scalar_value=opp)

    async def execute_side(*args, **kwargs):
        return opp_result

    async def flush_side():
        mock_db.add.call_args[0][0].id = _uid()

    mock_db.execute = AsyncMock(side_effect=execute_side)
    mock_db.flush = AsyncMock(side_effect=flush_side)

    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": str(opp.id), "notes": "Excited about this role"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["notes"] == "Excited about this role"
    assert data["stage"] == "saved"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_application_no_notes(auth_client, mock_db):
    opp = make_opportunity()
    opp_result = MockResult(scalar_value=opp)

    async def execute_side(*args, **kwargs):
        return opp_result

    async def flush_side():
        mock_db.add.call_args[0][0].id = _uid()

    mock_db.execute = AsyncMock(side_effect=execute_side)
    mock_db.flush = AsyncMock(side_effect=flush_side)

    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": str(opp.id)},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_application_opportunity_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": _uid()},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_application_invalid_id_format(auth_client, mock_db):
    async def flush_side():
        mock_db.add.call_args[0][0].id = _uid()

    mock_db.flush = AsyncMock(side_effect=flush_side)

    response = await auth_client.post(
        "/api/v1/applications",
        json={"opportunity_id": "not-a-uuid"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_application_missing_opportunity_id(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/applications",
        json={"notes": "Missing opp id"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_application_success(auth_client, mock_db):
    app_obj = make_application()
    app_result = MockResult(scalar_value=app_obj)
    mock_db.execute = AsyncMock(return_value=app_result)

    response = await auth_client.patch(
        f"/api/v1/applications/{app_obj.id}",
        json={"stage": "applied", "notes": "Updated notes"},
    )
    assert response.status_code == 200
    assert app_obj.stage == "applied"
    assert app_obj.notes == "Updated notes"


@pytest.mark.asyncio
async def test_update_application_stage_only(auth_client, mock_db):
    app_obj = make_application()
    app_result = MockResult(scalar_value=app_obj)
    mock_db.execute = AsyncMock(return_value=app_result)

    response = await auth_client.patch(
        f"/api/v1/applications/{app_obj.id}",
        json={"stage": "interview"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_application_next_step(auth_client, mock_db):
    app_obj = make_application()
    app_result = MockResult(scalar_value=app_obj)
    mock_db.execute = AsyncMock(return_value=app_result)

    response = await auth_client.patch(
        f"/api/v1/applications/{app_obj.id}",
        json={"next_step": "Phone screen", "next_date": "2026-06-15"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_application_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.patch(
        f"/api/v1/applications/{_uid()}",
        json={"stage": "applied"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_application_success(auth_client, mock_db):
    app_obj = make_application()
    app_result = MockResult(scalar_value=app_obj)
    mock_db.execute = AsyncMock(return_value=app_result)

    response = await auth_client.delete(f"/api/v1/applications/{app_obj.id}")
    assert response.status_code == 204
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_application_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.delete(f"/api/v1/applications/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_application_no_auth(async_client):
    response = await async_client.delete(f"/api/v1/applications/{_uid()}")
    assert response.status_code in (401, 403)
