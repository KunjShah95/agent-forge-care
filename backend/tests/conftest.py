import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

from httpx import AsyncClient, ASGITransport
from passlib.context import CryptContext

from app.main import app
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import (
    User,
    Profile,
    ProfileSkill,
    Skill,
    Opportunity,
    Application,
    ApplicationStage,
    Contact,
    ContactStatus,
    AgentTask,
    AgentType,
    TaskStatus,
    MemoryEntry,
    AlertConfig,
    MatchScore,
    PlannerGoal,
)
from app.api.v1.auth import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TEST_USER_ID = str(uuid.uuid4())
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"
TEST_USER_HASH = pwd_context.hash(TEST_USER_PASSWORD)
TEST_USER_NAME = "Test User"

OTHER_USER_ID = str(uuid.uuid4())


def _uid():
    return str(uuid.uuid4())


def make_user(**overrides) -> User:
    defaults = dict(
        id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        password_hash=TEST_USER_HASH,
        full_name=TEST_USER_NAME,
        avatar_url=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return User(**defaults)


def make_profile(user_id=None, **overrides) -> Profile:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        school="Test University",
        graduation_date=date(2026, 6, 1),
        bio="Test bio",
        portfolio_url="https://portfolio.test",
        linkedin_url="https://linkedin.com/in/test",
        github_url="https://github.com/test",
        target_locations=["Remote", "San Francisco"],
        salary_min=80000,
        salary_max=120000,
        role_types=["Internship", "Full-time"],
        company_sizes=["Startup", "Enterprise"],
        career_goal="ML Engineer",
        is_onboarded=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Profile(**defaults)


def make_opportunity(user_id=None, **overrides) -> Opportunity:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        title="ML Research Intern",
        company="TestCorp",
        company_logo=None,
        location="San Francisco",
        remote=True,
        type="Internship",
        salary_min=5000,
        salary_max=8000,
        salary_currency="USD",
        posted_date=date(2026, 1, 1),
        deadline=date(2026, 12, 31),
        description="Test opportunity description",
        apply_url="https://apply.test",
        company_size="Startup",
        skills_required=["Python", "PyTorch"],
        source="test",
        source_url=None,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Opportunity(**defaults)


def make_application(user_id=None, opp_id=None, **overrides) -> Application:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        opportunity_id=opp_id or _uid(),
        stage=ApplicationStage.saved,
        applied_date=date.today(),
        next_step=None,
        next_date=None,
        notes="Test notes",
        resume_version=None,
        cover_letter=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Application(**defaults)


def make_contact(user_id=None, **overrides) -> Contact:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        name="Jane Doe",
        role="Recruiter",
        company="TestCorp",
        email="jane@testcorp.com",
        linkedin_url="https://linkedin.com/in/jane",
        phone="+1234567890",
        status=ContactStatus.new,
        last_contact=None,
        notes="Test contact notes",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Contact(**defaults)


def make_agent_task(user_id=None, **overrides) -> AgentTask:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        agent_type=AgentType.planner,
        goal_id=None,
        input={"goal": "test goal"},
        output={},
        status=TaskStatus.queued,
        error=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return AgentTask(**defaults)


def make_memory_entry(user_id=None, **overrides) -> MemoryEntry:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        key="test_key",
        value={"data": "test_value"},
        weight=Decimal("1.00"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return MemoryEntry(**defaults)


def make_alert_config(user_id=None, **overrides) -> AlertConfig:
    defaults = dict(
        id=_uid(),
        user_id=user_id or TEST_USER_ID,
        name="Test Alert",
        keywords=["python", "ml"],
        locations=["Remote"],
        opportunity_types=["Internship"],
        min_match_score=80,
        frequency="daily",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return AlertConfig(**defaults)


def make_match_score(user_id=None, opp_id=None, **overrides) -> MatchScore:
    defaults = dict(
        id=_uid(),
        opportunity_id=opp_id or _uid(),
        user_id=user_id or TEST_USER_ID,
        overall_score=Decimal("85.50"),
        skill_score=Decimal("90.00"),
        location_score=Decimal("80.00"),
        experience_score=Decimal("85.00"),
        company_score=Decimal("87.00"),
        reasons=["Strong skill match", "Good location"],
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return MatchScore(**defaults)


class MockResult:
    def __init__(self, scalar_value=None, scalars_list=None):
        self._scalar_value = scalar_value
        self._scalars_list = scalars_list or []

    def scalar_one_or_none(self):
        return self._scalar_value

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = self._scalars_list
        return mock_scalars

    def all(self):
        return self._scalars_list


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def test_user():
    return make_user()


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_auth():
    token = create_access_token(str(OTHER_USER_ID))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def async_client(mock_db):
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(mock_db, test_user):
    async def override_get_db():
        yield mock_db

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


def setup_mock_execute(mock_db, results: list[MockResult]):
    if len(results) == 1:
        mock_db.execute = AsyncMock(return_value=results[0])
    else:
        mock_db.execute = AsyncMock(side_effect=results)
