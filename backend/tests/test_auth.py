import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import (
    MockResult,
    make_user,
    setup_mock_execute,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
    TEST_USER_NAME,
)


@pytest.mark.asyncio
async def test_register_success(async_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])
    mock_db.flush = AsyncMock()

    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client, mock_db):
    existing_user = make_user()
    setup_mock_execute(mock_db, [MockResult(scalar_value=existing_user)])

    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": TEST_USER_EMAIL,
            "password": "password123",
            "full_name": "Dup User",
        },
    )
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(async_client, mock_db):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "short",
            "full_name": "New User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(async_client, mock_db):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_name(async_client, mock_db):
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "password123",
            "full_name": "",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(async_client, mock_db):
    user = make_user()
    setup_mock_execute(mock_db, [MockResult(scalar_value=user)])

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, mock_db):
    user = make_user()
    setup_mock_execute(mock_db, [MockResult(scalar_value=user)])

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": TEST_USER_EMAIL, "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(async_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_email_format(async_client, mock_db):
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "bad", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token_success(async_client, mock_db):
    from app.services.auth_service import AuthService

    create_refresh_token = AuthService.create_refresh_token
    import uuid

    user_id = str(uuid.uuid4())
    refresh = create_refresh_token(user_id)
    setup_mock_execute(mock_db, [MockResult()])

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"token": refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token(async_client, mock_db):
    from app.services.auth_service import AuthService

    create_access_token = AuthService.create_access_token
    import uuid

    token = create_access_token(str(uuid.uuid4()))

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"token": token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(async_client, mock_db):
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"token": "invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_success(auth_client, test_user):
    response = await auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_get_me_no_token(async_client):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_invalid_token(async_client):
    response = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_me_success(auth_client, mock_db, test_user):
    setup_mock_execute(mock_db, [MockResult()])

    response = await auth_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_me_avatar(auth_client, mock_db, test_user):
    setup_mock_execute(mock_db, [MockResult()])

    response = await auth_client.patch(
        "/api/v1/auth/me",
        json={"avatar_url": "https://example.com/avatar.png"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_me_no_auth(async_client):
    response = await async_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated"},
    )
    assert response.status_code in (401, 403)
