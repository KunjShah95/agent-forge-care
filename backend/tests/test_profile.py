import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import (
    MockResult,
    make_profile,
    make_user,
    setup_mock_execute,
    _uid,
)
from app.models.user import Profile, ProfileSkill, Skill


@pytest.mark.asyncio
async def test_get_profile_existing(auth_client, mock_db):
    profile = make_profile()
    profile.skills = []
    setup_mock_execute(mock_db, [MockResult(scalar_value=profile)])

    response = await auth_client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["school"] == "Test University"
    assert data["career_goal"] == "ML Engineer"


@pytest.mark.asyncio
async def test_get_profile_creates_if_missing(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.get("/api/v1/profile")
    assert response.status_code == 200
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_profile_no_auth(async_client):
    response = await async_client.get("/api/v1/profile")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_profile(auth_client, mock_db):
    profile = make_profile()
    profile.skills = []
    setup_mock_execute(mock_db, [MockResult(scalar_value=profile)])

    response = await auth_client.put(
        "/api/v1/profile",
        json={
            "school": "New University",
            "bio": "Updated bio",
            "target_locations": ["New York"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["school"] == "New University"


@pytest.mark.asyncio
async def test_update_profile_creates_if_missing(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.put(
        "/api/v1/profile",
        json={"school": "New University"},
    )
    assert response.status_code == 200
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_update_profile_partial(auth_client, mock_db):
    profile = make_profile()
    profile.skills = []
    setup_mock_execute(mock_db, [MockResult(scalar_value=profile)])

    response = await auth_client.put(
        "/api/v1/profile",
        json={"salary_min": 90000},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_profile_onboarded(auth_client, mock_db):
    profile = make_profile(is_onboarded=False)
    profile.skills = []
    setup_mock_execute(mock_db, [MockResult(scalar_value=profile)])

    response = await auth_client.put(
        "/api/v1/profile",
        json={"is_onboarded": True},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_skills(auth_client, mock_db):
    skill = Skill(id=_uid(), name="Python")
    ps = MagicMock()
    ps.skill = skill
    ps.proficiency = "advanced"
    mock_result = MockResult(scalars_list=[ps])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/profile/skills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["skill"]["name"] == "Python"
    assert data[0]["proficiency"] == "advanced"


@pytest.mark.asyncio
async def test_get_skills_empty(auth_client, mock_db):
    mock_result = MockResult(scalars_list=[])
    mock_db.execute = AsyncMock(return_value=mock_result)

    response = await auth_client.get("/api/v1/profile/skills")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_add_skill_success(auth_client, mock_db):
    profile = make_profile()
    skill = Skill(id=_uid(), name="React")

    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=skill),
        MockResult(scalar_value=None),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.post(
        "/api/v1/profile/skills",
        json={"name": "React", "proficiency": "beginner"},
    )
    assert response.status_code == 201
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_add_skill_creates_new_skill(auth_client, mock_db):
    profile = make_profile()

    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=None),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.post(
        "/api/v1/profile/skills",
        json={"name": "NewSkill", "proficiency": "intermediate"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_add_skill_duplicate(auth_client, mock_db):
    profile = make_profile()
    skill = Skill(id=_uid(), name="Python")
    existing_ps = MagicMock()

    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=skill),
        MockResult(scalar_value=existing_ps),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.post(
        "/api/v1/profile/skills",
        json={"name": "Python"},
    )
    assert response.status_code == 409
    assert "already added" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_skill_creates_profile_if_missing(auth_client, mock_db):
    results = [
        MockResult(scalar_value=None),
        MockResult(scalar_value=None),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.post(
        "/api/v1/profile/skills",
        json={"name": "Go"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_remove_skill_success(auth_client, mock_db):
    profile = make_profile()
    ps = MagicMock()

    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=ps),
    ]
    setup_mock_execute(mock_db, results)

    skill_id = _uid()
    response = await auth_client.delete(f"/api/v1/profile/skills/{skill_id}")
    assert response.status_code == 204
    mock_db.delete.assert_called_once()


@pytest.mark.asyncio
async def test_remove_skill_no_profile(auth_client, mock_db):
    setup_mock_execute(mock_db, [MockResult(scalar_value=None)])

    response = await auth_client.delete(f"/api/v1/profile/skills/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_skill_not_found(auth_client, mock_db):
    profile = make_profile()
    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=None),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.delete(f"/api/v1/profile/skills/{_uid()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_skill_not_found(auth_client, mock_db):
    profile = make_profile()
    results = [
        MockResult(scalar_value=profile),
        MockResult(scalar_value=None),
    ]
    setup_mock_execute(mock_db, results)

    response = await auth_client.delete(f"/api/v1/profile/skills/{uuid.uuid4()}")
    assert response.status_code == 404
