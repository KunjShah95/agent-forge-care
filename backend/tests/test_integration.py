"""Integration tests — require a running PostgreSQL instance.

Run with: pytest tests/test_integration.py -x -v
Skip the default skipif by removing the skip or passing --run-integration.
"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
from app.models.user import (
    User,
    Profile,
    Opportunity,
    Application,
    ApplicationStage,
    MemoryEntry,
)

pytestmark = pytest.mark.skipif(
    True,
    reason="Integration tests require real PostgreSQL — run manually by removing skipif or adding --run-integration",
)

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge_test"


@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    connection = await engine.connect()
    transaction = await connection.begin()
    session = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )()
    yield session
    await transaction.rollback()
    await connection.close()


# ─── 1. Database health check ─────────────────────────────────────


@pytest.mark.asyncio
async def test_database_connectivity(db_session):
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


# ─── 2. User creation and retrieval ────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_retrieve_user(db_session):
    user_id = uuid.uuid4()
    ts = datetime.now(timezone.utc)
    user = User(
        id=user_id,
        email="integration-test@example.com",
        full_name="Integration Test User",
        firebase_uid="firebase-integration-test",
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(select(User).where(User.id == user_id))
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.email == "integration-test@example.com"
    assert fetched.full_name == "Integration Test User"
    assert fetched.firebase_uid == "firebase-integration-test"


@pytest.mark.asyncio
async def test_user_unique_email_constraint(db_session):
    ts = datetime.now(timezone.utc)
    user1 = User(
        id=uuid.uuid4(),
        email="duplicate-test@example.com",
        full_name="First User",
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(user1)
    await db_session.flush()

    user2 = User(
        id=uuid.uuid4(),
        email="duplicate-test@example.com",
        full_name="Second User",
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(user2)
    with pytest.raises(Exception):
        await db_session.flush()


@pytest.mark.asyncio
async def test_find_user_by_email(db_session):
    ts = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="find-by-email@example.com",
        full_name="Find By Email",
        firebase_uid="firebase-find-email",
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(
        select(User).where(User.email == "find-by-email@example.com")
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.full_name == "Find By Email"


@pytest.mark.asyncio
async def test_user_without_firebase_uid(db_session):
    ts = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="no-firebase@example.com",
        full_name="No Firebase UID",
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(user)
    await db_session.flush()

    result = await db_session.execute(
        select(User).where(User.firebase_uid.is_(None))
    )
    match = result.scalars().all()
    fetched = [u for u in match if u.email == "no-firebase@example.com"]
    assert len(fetched) == 1


# ─── 3. Profile CRUD ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_profile_crud(db_session):
    user = User(
        id=uuid.uuid4(),
        email="profile-test@example.com",
        full_name="Profile Test User",
        firebase_uid="firebase-profile-test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    profile = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        school="Integration University",
        bio="Integration test bio",
        target_locations=["Remote", "New York"],
        role_types=["Full-time"],
        career_goal="Backend Engineer",
        is_onboarded=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.flush()

    result = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.school == "Integration University"
    assert fetched.career_goal == "Backend Engineer"
    assert fetched.is_onboarded is False
    assert fetched.target_locations == ["Remote", "New York"]

    fetched.school = "Updated University"
    fetched.is_onboarded = True
    fetched.target_locations = ["San Francisco"]
    await db_session.flush()
    await db_session.refresh(fetched)

    assert fetched.school == "Updated University"
    assert fetched.is_onboarded is True
    assert fetched.target_locations == ["San Francisco"]

    await db_session.delete(fetched)
    await db_session.flush()

    result = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_profile_unique_user_id(db_session):
    user = User(
        id=uuid.uuid4(),
        email="profile-unique-test@example.com",
        full_name="Profile Unique User",
        firebase_uid="firebase-profile-unique",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    p1 = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        school="First School",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(p1)
    await db_session.flush()

    p2 = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        school="Second School",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(p2)
    with pytest.raises(Exception):
        await db_session.flush()


@pytest.mark.asyncio
async def test_profile_cascade_delete(db_session):
    user = User(
        id=uuid.uuid4(),
        email="cascade-delete@example.com",
        full_name="Cascade Delete User",
        firebase_uid="firebase-cascade",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    profile = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        school="Cascade University",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.flush()

    await db_session.delete(user)
    await db_session.flush()

    result = await db_session.execute(
        select(Profile).where(Profile.id == profile.id)
    )
    assert result.scalar_one_or_none() is None


# ─── 4. Opportunity CRUD ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_opportunity_crud(db_session):
    user = User(
        id=uuid.uuid4(),
        email="opp-test@example.com",
        full_name="Opportunity Test User",
        firebase_uid="firebase-opp-test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    opp = Opportunity(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Integration Intern",
        company="IntegrateCorp",
        location="Remote",
        remote=True,
        type="Internship",
        description="An integration test opportunity",
        skills_required=["Python", "SQL"],
        source="test",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(opp)
    await db_session.flush()

    result = await db_session.execute(
        select(Opportunity).where(Opportunity.user_id == user.id)
    )
    items = result.scalars().all()
    assert len(items) == 1
    assert items[0].title == "Integration Intern"

    result = await db_session.execute(
        select(Opportunity).where(
            Opportunity.user_id == user.id,
            Opportunity.type == "Internship",
            Opportunity.remote.is_(True),
        )
    )
    filtered = result.scalars().all()
    assert len(filtered) == 1

    opp2 = Opportunity(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Full-time Engineer",
        company="IntegrateCorp",
        location="New York",
        remote=False,
        type="Full-time",
        description="A full-time role",
        skills_required=["Python"],
        source="test",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(opp2)
    await db_session.flush()

    result = await db_session.execute(
        select(Opportunity).where(Opportunity.user_id == user.id)
    )
    items = result.scalars().all()
    assert len(items) == 2

    await db_session.delete(opp)
    await db_session.flush()

    result = await db_session.execute(
        select(Opportunity).where(Opportunity.user_id == user.id)
    )
    remaining = result.scalars().all()
    assert len(remaining) == 1
    assert remaining[0].title == "Full-time Engineer"


@pytest.mark.asyncio
async def test_opportunity_filter_by_type_and_active(db_session):
    user = User(
        id=uuid.uuid4(),
        email="opp-filter@example.com",
        full_name="Opportunity Filter User",
        firebase_uid="firebase-opp-filter",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    ts = datetime.now(timezone.utc)
    for title, otype in [("Intern A", "Internship"), ("Intern B", "Internship"), ("Full-time", "Full-time")]:
        opp = Opportunity(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title,
            company="FilterCorp",
            type=otype,
            description=title,
            source="test",
            is_active=True,
            created_at=ts,
            updated_at=ts,
        )
        db_session.add(opp)
    await db_session.flush()

    result = await db_session.execute(
        select(Opportunity).where(
            Opportunity.user_id == user.id,
            Opportunity.type == "Internship",
        )
    )
    internships = result.scalars().all()
    assert len(internships) == 2

    result = await db_session.execute(
        select(Opportunity).where(
            Opportunity.user_id == user.id,
            Opportunity.is_active.is_(True),
        )
    )
    active = result.scalars().all()
    assert len(active) == 3

    opp = (await db_session.execute(
        select(Opportunity).where(
            Opportunity.user_id == user.id,
            Opportunity.title == "Full-time",
        )
    )).scalar_one_or_none()
    opp.is_active = False
    await db_session.flush()

    result = await db_session.execute(
        select(Opportunity).where(
            Opportunity.user_id == user.id,
            Opportunity.is_active.is_(False),
        )
    )
    inactive = result.scalars().all()
    assert len(inactive) == 1
    assert inactive[0].title == "Full-time"


# ─── 5. MemoryEntry CRUD ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_memory_entry_with_ttl(db_session):
    user = User(
        id=uuid.uuid4(),
        email="memory-test@example.com",
        full_name="Memory Test User",
        firebase_uid="firebase-memory-test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    entry = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user.id,
        key="skill_preference",
        value={"skill": "Python"},
        weight=Decimal("1.00"),
        ttl_days=30,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(MemoryEntry).where(MemoryEntry.user_id == user.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.key == "skill_preference"
    assert fetched.value == {"skill": "Python"}
    assert fetched.weight == Decimal("1.00")
    assert fetched.ttl_days == 30

    entry_no_ttl = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user.id,
        key="permanent_pref",
        value={"theme": "dark"},
        weight=Decimal("0.80"),
        ttl_days=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(entry_no_ttl)
    await db_session.flush()

    result = await db_session.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.ttl_days.isnot(None),
        )
    )
    with_ttl = result.scalars().all()
    assert len(with_ttl) == 1
    assert with_ttl[0].key == "skill_preference"

    result = await db_session.execute(
        select(MemoryEntry).where(
            MemoryEntry.user_id == user.id,
            MemoryEntry.ttl_days.is_(None),
        )
    )
    without_ttl = result.scalars().all()
    assert len(without_ttl) == 1
    assert without_ttl[0].key == "permanent_pref"


@pytest.mark.asyncio
async def test_memory_entry_ttl_cleanup_query(db_session):
    user = User(
        id=uuid.uuid4(),
        email="memory-ttl-cleanup@example.com",
        full_name="Memory TTL Cleanup User",
        firebase_uid="firebase-memory-ttl",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    ts = datetime.now(timezone.utc)
    recent_entry = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user.id,
        key="recent",
        value={"data": "just_created"},
        weight=Decimal("1.00"),
        ttl_days=365,
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(recent_entry)

    no_ttl_entry = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user.id,
        key="permanent",
        value={"data": "no_expiry"},
        weight=Decimal("1.00"),
        ttl_days=None,
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(no_ttl_entry)
    await db_session.flush()

    expired_query = select(MemoryEntry).where(
        MemoryEntry.user_id == user.id,
        MemoryEntry.ttl_days.isnot(None),
        MemoryEntry.created_at + func.make_interval(0, 0, 0, 0, 0, 0, MemoryEntry.ttl_days) < func.now(),
    )
    result = await db_session.execute(expired_query)
    expired = result.scalars().all()
    assert len(expired) == 0

    with_ttl_query = select(MemoryEntry).where(
        MemoryEntry.user_id == user.id,
        MemoryEntry.ttl_days.isnot(None),
    )
    result = await db_session.execute(with_ttl_query)
    with_ttl = result.scalars().all()
    assert len(with_ttl) == 1
    assert with_ttl[0].key == "recent"

    result = await db_session.execute(
        select(func.count()).select_from(MemoryEntry).where(MemoryEntry.user_id == user.id)
    )
    total = result.scalar()
    assert total == 2


@pytest.mark.asyncio
async def test_memory_entry_multiple_per_user(db_session):
    user = User(
        id=uuid.uuid4(),
        email="memory-multi@example.com",
        full_name="Memory Multi User",
        firebase_uid="firebase-memory-multi",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    ts = datetime.now(timezone.utc)
    entries = []
    for i in range(5):
        entry = MemoryEntry(
            id=uuid.uuid4(),
            user_id=user.id,
            key=f"key_{i}",
            value={"index": i},
            weight=Decimal(f"0.{i}5") if i > 0 else Decimal("1.00"),
            ttl_days=None,
            created_at=ts,
            updated_at=ts,
        )
        db_session.add(entry)
        entries.append(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user.id)
        .order_by(MemoryEntry.key)
    )
    fetched = result.scalars().all()
    assert len(fetched) == 5

    for i, entry in enumerate(fetched):
        assert entry.value["index"] < 5


# ─── 6. Full application lifecycle ────────────────────────────────


@pytest.mark.asyncio
async def test_full_application_lifecycle(db_session):
    user = User(
        id=uuid.uuid4(),
        email="lifecycle-test@example.com",
        full_name="Lifecycle User",
        firebase_uid="firebase-lifecycle-test",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    profile = Profile(
        id=uuid.uuid4(),
        user_id=user.id,
        school="Lifecycle University",
        bio="Testing full lifecycle",
        career_goal="Full-stack Engineer",
        is_onboarded=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(profile)
    await db_session.flush()

    opp = Opportunity(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Lifecycle Engineer",
        company="LifecycleCorp",
        location="San Francisco",
        type="Full-time",
        description="A lifecycle test opportunity",
        skills_required=["Python", "React"],
        source="test",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(opp)
    await db_session.flush()

    result = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    assert result.scalar_one_or_none() is not None

    result = await db_session.execute(
        select(Opportunity).where(Opportunity.id == opp.id)
    )
    assert result.scalar_one_or_none() is not None

    app_entry = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        opportunity_id=opp.id,
        stage=ApplicationStage.saved,
        notes="Lifecycle test application",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(app_entry)
    await db_session.flush()

    result = await db_session.execute(
        select(Application).where(Application.user_id == user.id)
    )
    fetched_app = result.scalar_one_or_none()
    assert fetched_app is not None
    assert fetched_app.stage == ApplicationStage.saved
    assert fetched_app.notes == "Lifecycle test application"
    assert str(fetched_app.opportunity_id) == str(opp.id)

    fetched_app.stage = ApplicationStage.interview
    fetched_app.notes = "Moved to interview stage"
    await db_session.flush()
    await db_session.refresh(fetched_app)
    assert fetched_app.stage == ApplicationStage.interview
    assert fetched_app.notes == "Moved to interview stage"

    fetched_app.stage = ApplicationStage.offer
    await db_session.flush()
    await db_session.refresh(fetched_app)
    assert fetched_app.stage == ApplicationStage.offer

    await db_session.delete(fetched_app)
    await db_session.flush()

    result = await db_session.execute(
        select(Application).where(Application.user_id == user.id)
    )
    assert result.scalar_one_or_none() is None

    result = await db_session.execute(
        select(Opportunity).where(Opportunity.id == opp.id)
    )
    assert result.scalar_one_or_none() is not None

    result = await db_session.execute(
        select(Profile).where(Profile.user_id == user.id)
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_application_stage_transitions(db_session):
    user = User(
        id=uuid.uuid4(),
        email="app-stages@example.com",
        full_name="App Stages User",
        firebase_uid="firebase-app-stages",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    opp = Opportunity(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Stages Role",
        company="StagesCorp",
        type="Full-time",
        description="Test stage transitions",
        source="test",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(opp)
    await db_session.flush()

    app_entry = Application(
        id=uuid.uuid4(),
        user_id=user.id,
        opportunity_id=opp.id,
        stage=ApplicationStage.saved,
        applied_date=date.today(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(app_entry)
    await db_session.flush()

    stages = [
        ApplicationStage.applied,
        ApplicationStage.oa,
        ApplicationStage.interview,
        ApplicationStage.offer,
        ApplicationStage.rejected,
    ]
    for stage in stages:
        app_entry.stage = stage
        await db_session.flush()
        await db_session.refresh(app_entry)
        assert app_entry.stage == stage


@pytest.mark.asyncio
async def test_cascade_delete_removes_related(db_session):
    user = User(
        id=uuid.uuid4(),
        email="full-cascade@example.com",
        full_name="Full Cascade User",
        firebase_uid="firebase-full-cascade",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()

    ts = datetime.now(timezone.utc)
    opps = []
    for i in range(3):
        opp = Opportunity(
            id=uuid.uuid4(),
            user_id=user.id,
            title=f"Opp {i}",
            company="CascadeCorp",
            type="Internship",
            description=f"Opportunity {i}",
            source="test",
            is_active=True,
            created_at=ts,
            updated_at=ts,
        )
        db_session.add(opp)
        opps.append(opp)
    await db_session.flush()

    apps = []
    for i, opp in enumerate(opps):
        app_entry = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            opportunity_id=opp.id,
            stage=ApplicationStage.saved,
            notes=f"App {i}",
            created_at=ts,
            updated_at=ts,
        )
        db_session.add(app_entry)
        apps.append(app_entry)
    await db_session.flush()

    mem_entry = MemoryEntry(
        id=uuid.uuid4(),
        user_id=user.id,
        key="test_key",
        value={"data": "test"},
        weight=Decimal("1.00"),
        ttl_days=None,
        created_at=ts,
        updated_at=ts,
    )
    db_session.add(mem_entry)
    await db_session.flush()

    await db_session.delete(user)
    await db_session.flush()

    result = await db_session.execute(
        select(func.count()).select_from(Opportunity).where(Opportunity.user_id == user.id)
    )
    assert result.scalar() == 0

    result = await db_session.execute(
        select(func.count()).select_from(Application).where(Application.user_id == user.id)
    )
    assert result.scalar() == 0

    result = await db_session.execute(
        select(func.count()).select_from(MemoryEntry).where(MemoryEntry.user_id == user.id)
    )
    assert result.scalar() == 0
