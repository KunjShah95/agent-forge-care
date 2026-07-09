import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    ARRAY,
    DECIMAL,
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return uuid.uuid4()


# ─── Enums ──────────────────────────────────────────────────


class ApplicationStage(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    oa = "oa"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class ContactStatus(str, enum.Enum):
    new = "new"
    reached_out = "reached_out"
    replied = "replied"
    meeting = "meeting"
    closed = "closed"


class TaskStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentType(str, enum.Enum):
    planner = "planner"
    internship = "internship"
    job = "job"
    research = "research"
    resume = "resume"
    interview = "interview"
    networking = "networking"
    monitor = "monitor"


class OpportunityType(str, enum.Enum):
    internship = "Internship"
    full_time = "Full-time"
    hackathon = "Hackathon"
    scholarship = "Scholarship"
    fellowship = "Fellowship"
    research = "Research"


# ─── Users ──────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    email_verified = Column(Boolean, default=False, nullable=False, server_default="false")
    password_hash = Column(String(255), nullable=True)
    firebase_uid = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="user", cascade="all, delete-orphan")
    memory_entries = relationship("MemoryEntry", back_populates="user", cascade="all, delete-orphan")
    planner_goals = relationship("PlannerGoal", back_populates="user", cascade="all, delete-orphan")
    match_scores = relationship("MatchScore", back_populates="user", cascade="all, delete-orphan")
    alert_configs = relationship("AlertConfig", back_populates="user", cascade="all, delete-orphan")


# ─── Profiles ───────────────────────────────────────────────


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    school = Column(String(255), nullable=True)
    graduation_date = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    portfolio_url = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    github_url = Column(Text, nullable=True)
    target_locations = Column(ARRAY(String), default=list)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    role_types = Column(ARRAY(String), default=list)
    company_sizes = Column(ARRAY(String), default=list)
    career_goal = Column(Text, nullable=True)
    is_onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="profile")
    skills = relationship("ProfileSkill", back_populates="profile", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False)


class ProfileSkill(Base):
    __tablename__ = "profile_skills"
    __table_args__ = (UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),)

    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    skill_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    )
    proficiency = Column(String(20), default="intermediate")

    profile = relationship("Profile", back_populates="skills")
    skill = relationship("Skill")


# ─── Opportunities ──────────────────────────────────────────


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    company_logo = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    city = Column(String(150), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    industry = Column(String(150), nullable=True, index=True)
    remote = Column(Boolean, default=False)
    work_type = Column(String(20), nullable=True)
    type = Column(String(50), nullable=False, index=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(String(3), default="USD")
    posted_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True, index=True)
    description = Column(Text, nullable=True)
    apply_url = Column(Text, nullable=True)
    company_size = Column(String(50), nullable=True)
    skills_required = Column(ARRAY(String), default=list, index=True)
    source = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="opportunities")
    match_scores = relationship("MatchScore", back_populates="opportunity", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="opportunity", cascade="all, delete-orphan")


class MatchScore(Base):
    __tablename__ = "match_scores"
    __table_args__ = (UniqueConstraint("opportunity_id", "user_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    opportunity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(DECIMAL(5, 2), nullable=False)
    skill_score = Column(DECIMAL(5, 2), nullable=True)
    location_score = Column(DECIMAL(5, 2), nullable=True)
    experience_score = Column(DECIMAL(5, 2), nullable=True)
    company_score = Column(DECIMAL(5, 2), nullable=True)
    reasons = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    opportunity = relationship("Opportunity", back_populates="match_scores")
    user = relationship("User", back_populates="match_scores")


# ─── Applications ───────────────────────────────────────────


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage = Column(Enum(ApplicationStage), default=ApplicationStage.saved, index=True)
    applied_date = Column(Date, nullable=True)
    next_step = Column(Text, nullable=True)
    next_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    resume_version = Column(Text, nullable=True)
    cover_letter = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="applications")
    opportunity = relationship("Opportunity", back_populates="applications")


# ─── Contacts ───────────────────────────────────────────────


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    linkedin_url = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    status = Column(Enum(ContactStatus), default=ContactStatus.new, index=True)
    last_contact = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="contacts")


# ─── Agent Tasks ────────────────────────────────────────────


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type = Column(Enum(AgentType), nullable=False)
    goal_id = Column(UUID(as_uuid=True), nullable=True)
    input = Column(JSON, default=dict)
    output = Column(JSON, default=dict)
    status = Column(Enum(TaskStatus), default=TaskStatus.queued, index=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user = relationship("User", back_populates="agent_tasks")


# ─── Planner Goals ──────────────────────────────────────────


class PlannerGoal(Base):
    __tablename__ = "planner_goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_text = Column(Text, nullable=False)
    plan = Column(JSON, default=list)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="planner_goals")


# ─── Memory Entries ─────────────────────────────────────────


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key = Column(String(255), nullable=False)
    value = Column(JSON, nullable=False)
    weight = Column(DECIMAL(3, 2), default=1.0)
    ttl_days = Column(Integer, nullable=True, default=90)  # Auto-expire after 90 days
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="memory_entries")


# ─── Alert Configs ──────────────────────────────────────────


class AlertConfig(Base):
    __tablename__ = "alert_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=gen_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    keywords = Column(ARRAY(String), default=list)
    locations = Column(ARRAY(String), default=list)
    opportunity_types = Column(ARRAY(String), default=list)
    min_match_score = Column(Integer, default=80)
    frequency = Column(String(20), default="daily")
    is_active = Column(Boolean, default=True)
    email_notify = Column(Boolean, default=False, server_default="false", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user = relationship("User", back_populates="alert_configs")
