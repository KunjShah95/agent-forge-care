from unittest.mock import AsyncMock

import pytest

from tests.conftest import (
    MockResult,
    _uid,
    make_memory_entry,
    setup_mock_execute,
)


@pytest.mark.asyncio
async def test_list_memory(auth_client, mock_db):
    entry = make_memory_entry()
    count_result = MockResult(scalar_value=1)
    entries_result = MockResult(scalars_list=[entry])

    mock_db.execute = AsyncMock(side_effect=[count_result, entries_result])

    response = await auth_client.get("/api/v1/memory")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["key"] == "test_key"


@pytest.mark.asyncio
async def test_list_memory_empty(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    entries_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, entries_result])

    response = await auth_client.get("/api/v1/memory")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_memory_pagination(auth_client, mock_db):
    count_result = MockResult(scalar_value=50)
    entries_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, entries_result])

    response = await auth_client.get("/api/v1/memory?page=3&limit=10")
    assert response.status_code == 200
    assert response.json()["page"] == 3


@pytest.mark.asyncio
async def test_list_memory_no_auth(async_client):
    response = await async_client.get("/api/v1/memory")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_memory_success(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/memory",
        json={
            "key": "preferred_languages",
            "value": ["Python", "TypeScript"],
            "weight": 0.9,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "preferred_languages"
    assert data["weight"] == 0.9
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_memory_default_weight(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/memory",
        json={"key": "career_goal", "value": "ML Engineer at FAANG"},
    )
    assert response.status_code == 201
    assert response.json()["weight"] == 1.0


@pytest.mark.asyncio
async def test_create_memory_complex_value(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/memory",
        json={
            "key": "interview_prep",
            "value": {
                "companies": ["Google", "Meta"],
                "topics": ["system design", "algorithms"],
                "progress": 0.6,
            },
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_memory_missing_key(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/memory",
        json={"value": "some value"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_memory_missing_value(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/memory",
        json={"key": "test"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_memory_success(auth_client, mock_db):
    entry = make_memory_entry()
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])

    response = await auth_client.patch(
        f"/api/v1/memory/{entry.id}",
        json={"value": {"updated": True}, "weight": 0.5},
    )
    assert response.status_code == 200
    assert entry.value == {"updated": True}
    assert entry.weight == 0.5


@pytest.mark.asyncio
async def test_update_memory_value_only(auth_client, mock_db):
    entry = make_memory_entry()
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])

    response = await auth_client.patch(
        f"/api/v1/memory/{entry.id}",
        json={"value": "new value"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_memory_weight_only(auth_client, mock_db):
    entry = make_memory_entry()
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])

    response = await auth_client.patch(
        f"/api/v1/memory/{entry.id}",
        json={"weight": 0.3},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_memory_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.patch(
        f"/api/v1/memory/{_uid()}",
        json={"value": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory_success(auth_client, mock_db):
    entry = make_memory_entry()
    setup_mock_execute(mock_db, [MockResult(scalar_value=entry)])

    response = await auth_client.delete(f"/api/v1/memory/{entry.id}")
    assert response.status_code == 204
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_memory_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.delete(f"/api/v1/memory/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_memory_no_auth(async_client):
    response = await async_client.delete(f"/api/v1/memory/{_uid()}")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_memory_context(auth_client, mock_db):
    entry1 = make_memory_entry(key="goal", value="ML Engineer")
    entry2 = make_memory_entry(key="location", value="Remote")
    mock_result = MockResult(scalars_list=[entry1, entry2])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/memory/context")
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "ML Engineer"
    assert data["location"] == "Remote"


@pytest.mark.asyncio
async def test_get_memory_context_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/memory/context")
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.asyncio
async def test_list_memory_invalid_page(auth_client, mock_db):
    response = await auth_client.get("/api/v1/memory?page=-1")
    assert response.status_code == 422
