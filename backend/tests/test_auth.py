import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from tests.conftest import (
    make_user,
    create_firebase_token,
    TEST_USER_EMAIL,
    TEST_USER_NAME,
    TEST_FIREBASE_UID,
)

# ─── GET /me ─────────────────────────────────────────────────


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
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401


# ─── Firebase Token Verification ─────────────────────────────


@pytest.mark.asyncio
async def test_verify_firebase_token_valid():
    """A valid Firebase token should decode successfully."""
    from app.dependencies import verify_firebase_token, _certs_cache

    _certs_cache["certs"] = None
    _certs_cache["expires_at"] = 0.0

    token = create_firebase_token()

    from tests.conftest import TEST_PRIVATE_KEY

    from cryptography.hazmat.primitives import serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    import datetime

    private_k = serialization.load_pem_private_key(TEST_PRIVATE_KEY, password=None)

    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "US")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_k.public_key())
        .serial_number(1000)
        .not_valid_before(datetime.datetime(2024, 1, 1))
        .not_valid_after(datetime.datetime(2034, 1, 1))
        .sign(private_k, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()

    with patch("app.dependencies._get_certs_sync", return_value={"test-kid-001": cert_pem}):
        payload = verify_firebase_token(token)
        assert payload["sub"] == TEST_FIREBASE_UID
        assert payload["email"] == TEST_USER_EMAIL


@pytest.mark.asyncio
async def test_verify_firebase_token_wrong_key():
    """A token signed with the wrong key should be rejected."""
    from app.dependencies import verify_firebase_token, _certs_cache

    _certs_cache["certs"] = None
    _certs_cache["expires_at"] = 0.0

    token = create_firebase_token()

    from cryptography.hazmat.primitives import serialization
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    import datetime

    wrong_key = __import__(
        "cryptography.hazmat.primitives.asymmetric.rsa", fromlist=["rsa"]
    ).generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COUNTRY_NAME, "US")])
    wrong_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(wrong_key.public_key())
        .serial_number(1000)
        .not_valid_before(datetime.datetime(2024, 1, 1))
        .not_valid_after(datetime.datetime(2034, 1, 1))
        .sign(wrong_key, hashes.SHA256())
    )
    wrong_cert_pem = wrong_cert.public_bytes(serialization.Encoding.PEM).decode()

    with patch(
        "app.dependencies._get_certs_sync", return_value={"test-kid-001": wrong_cert_pem}
    ):
        with pytest.raises(ValueError, match="Token verification failed"):
            verify_firebase_token(token)


@pytest.mark.asyncio
async def test_verify_firebase_token_missing_kid():
    """A token without a kid in the header should be rejected."""
    from jose import jws
    from app.dependencies import verify_firebase_token, _certs_cache

    _certs_cache["certs"] = None
    _certs_cache["expires_at"] = 0.0

    payload = {"sub": "test", "email": "test@test.com"}
    header = {"alg": "RS256", "typ": "JWT"}
    token = jws.sign(
        payload,
        __import__("tests.conftest", fromlist=["TEST_PRIVATE_KEY"]).TEST_PRIVATE_KEY,
        algorithm="RS256",
        headers=header,
    )

    with pytest.raises(ValueError, match="No kid in token header"):
        verify_firebase_token(token)


# ─── Auto-Provisioning ───────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_provision_new_user(async_client, mock_db):
    """A valid Firebase token for a new email should auto-create User + Profile."""
    from app.dependencies import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials

    new_email = "newfirebase@example.com"
    new_uid = "new-firebase-uid-999"

    mock_db.execute = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),
        MagicMock(scalar_one_or_none=lambda: None),
    ]

    with patch(
        "app.dependencies.verify_firebase_token",
        return_value={
            "sub": new_uid,
            "email": new_email,
            "name": "New Firebase User",
            "email_verified": True,
            "aud": "test-firebase-project",
            "iss": "https://securetoken.google.com/test-firebase-project",
        },
    ):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        user = await get_current_user(credentials=creds, db=mock_db)

        assert user.email == new_email
        assert user.firebase_uid == new_uid
        assert user.email_verified is True
        assert user.password_hash is None
        assert user.full_name == "New Firebase User"
        assert mock_db.add.called


@pytest.mark.asyncio
async def test_auto_provision_links_existing_user(async_client, mock_db):
    """An existing user without firebase_uid should get linked on Firebase login."""
    from app.dependencies import get_current_user
    from fastapi.security import HTTPAuthorizationCredentials

    existing_user = make_user(firebase_uid=None)

    mock_db.execute = AsyncMock()
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),
        MagicMock(scalar_one_or_none=lambda: existing_user),
    ]

    with patch(
        "app.dependencies.verify_firebase_token",
        return_value={
            "sub": TEST_FIREBASE_UID,
            "email": TEST_USER_EMAIL,
            "name": TEST_USER_NAME,
            "email_verified": True,
            "aud": "test-firebase-project",
            "iss": "https://securetoken.google.com/test-firebase-project",
        },
    ):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
        user = await get_current_user(credentials=creds, db=mock_db)

        assert user.id == existing_user.id
        assert user.firebase_uid == TEST_FIREBASE_UID
        assert user.email_verified is True


# ─── PATCH /me ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_me_success(auth_client, mock_db, test_user):
    response = await auth_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_me_avatar(auth_client, mock_db, test_user):
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


# ─── Redis Rate Limiter ──────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    from app.dependencies import RedisRateLimiter

    limiter = RedisRateLimiter("redis://localhost:6379")
    limiter._redis = AsyncMock()
    pipeline = MagicMock()
    pipeline.zremrangebyscore = MagicMock()
    pipeline.zcard = MagicMock(return_value=5)
    pipeline.zadd = MagicMock()
    pipeline.expire = MagicMock()
    pipeline.execute = AsyncMock(return_value=(None, 5, None, True))
    limiter._redis.pipeline = MagicMock(return_value=pipeline)

    result = await limiter.is_rate_limited("test:key", 10, 60)
    assert result is False


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    from app.dependencies import RedisRateLimiter

    limiter = RedisRateLimiter("redis://localhost:6379")
    limiter._redis = AsyncMock()
    pipeline = MagicMock()
    pipeline.zremrangebyscore = MagicMock()
    pipeline.zcard = MagicMock(return_value=10)
    pipeline.zadd = MagicMock()
    pipeline.expire = MagicMock()
    pipeline.execute = AsyncMock(return_value=(None, 10, None, True))
    limiter._redis.pipeline = MagicMock(return_value=pipeline)

    result = await limiter.is_rate_limited("test:key", 10, 60)
    assert result is True
