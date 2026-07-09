from unittest.mock import AsyncMock

import pytest

from tests.conftest import (
    MockResult,
    _uid,
    make_contact,
    setup_mock_execute,
)


@pytest.mark.asyncio
async def test_list_contacts(auth_client, mock_db):
    contact = make_contact()
    count_result = MockResult(scalar_value=1)
    contact_result = MockResult(scalars_list=[contact])

    mock_db.execute = AsyncMock(side_effect=[count_result, contact_result])

    response = await auth_client.get("/api/v1/contacts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_list_contacts_empty(auth_client, mock_db):
    count_result = MockResult(scalar_value=0)
    contact_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, contact_result])

    response = await auth_client.get("/api/v1/contacts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_contacts_pagination(auth_client, mock_db):
    count_result = MockResult(scalar_value=30)
    contact_result = MockResult(scalars_list=[])

    mock_db.execute = AsyncMock(side_effect=[count_result, contact_result])

    response = await auth_client.get("/api/v1/contacts?page=2&limit=5")
    assert response.status_code == 200
    assert response.json()["page"] == 2


@pytest.mark.asyncio
async def test_list_contacts_no_auth(async_client):
    response = await async_client.get("/api/v1/contacts")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_contact_success(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/contacts",
        json={
            "name": "John Smith",
            "role": "Engineering Manager",
            "company": "BigTech",
            "email": "john@bigtech.com",
            "linkedin_url": "https://linkedin.com/in/john",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Smith"
    assert data["status"] == "new"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_contact_minimal(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/contacts",
        json={"name": "Minimal Contact"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_contact_missing_name(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/contacts",
        json={"role": "Recruiter"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_contact_invalid_email(auth_client, mock_db):
    response = await auth_client.post(
        "/api/v1/contacts",
        json={"name": "Test", "email": "not-valid"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_contact_success(auth_client, mock_db):
    contact = make_contact()
    contact_result = MockResult(scalar_value=contact)
    mock_db.execute = AsyncMock(return_value=contact_result)

    response = await auth_client.patch(
        f"/api/v1/contacts/{contact.id}",
        json={"status": "reached_out", "notes": "Sent LinkedIn message"},
    )
    assert response.status_code == 200
    assert contact.status == "reached_out"
    assert contact.notes == "Sent LinkedIn message"


@pytest.mark.asyncio
async def test_update_contact_name(auth_client, mock_db):
    contact = make_contact()
    contact_result = MockResult(scalar_value=contact)
    mock_db.execute = AsyncMock(return_value=contact_result)

    response = await auth_client.patch(
        f"/api/v1/contacts/{contact.id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_contact_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.patch(
        f"/api/v1/contacts/{_uid()}",
        json={"name": "Nobody"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_contact_success(auth_client, mock_db):
    contact = make_contact()
    contact_result = MockResult(scalar_value=contact)
    mock_db.execute = AsyncMock(return_value=contact_result)

    response = await auth_client.delete(f"/api/v1/contacts/{contact.id}")
    assert response.status_code == 204
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_contact_not_found(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.delete(f"/api/v1/contacts/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_contact_no_auth(async_client):
    response = await async_client.delete(f"/api/v1/contacts/{_uid()}")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_contact_last_contact(auth_client, mock_db):
    contact = make_contact()
    contact_result = MockResult(scalar_value=contact)
    mock_db.execute = AsyncMock(return_value=contact_result)

    response = await auth_client.patch(
        f"/api/v1/contacts/{contact.id}",
        json={"last_contact": "2026-05-20"},
    )
    assert response.status_code == 200
