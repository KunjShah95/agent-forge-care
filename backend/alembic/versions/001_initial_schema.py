"""empty message

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema for AgentForge Career OS."""
    # Enable UUID extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Enums
    op.execute("""
        CREATE TYPE application_stage AS ENUM (
            'saved', 'applied', 'oa', 'interview', 'offer', 'rejected', 'withdrawn'
        )
    """)
    op.execute("""
        CREATE TYPE contact_status AS ENUM (
            'new', 'reached_out', 'replied', 'meeting', 'closed'
        )
    """)
    op.execute("""
        CREATE TYPE task_status AS ENUM (
            'queued', 'running', 'completed', 'failed'
        )
    """)
    op.execute("""
        CREATE TYPE agent_type AS ENUM (
            'planner', 'internship', 'job', 'research', 'resume',
            'interview', 'networking', 'monitor'
        )
    """)

    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])

    op.create_table(
        "profiles",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("school", sa.String(255), nullable=True),
        sa.Column("graduation_date", sa.Date(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("portfolio_url", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("github_url", sa.Text(), nullable=True),
        sa.Column("target_locations", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("role_types", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("company_sizes", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("career_goal", sa.Text(), nullable=True),
        sa.Column("is_onboarded", sa.Boolean(), server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "skills",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
    )
    op.create_index("idx_skills_name", "skills", ["name"])

    op.create_table(
        "profile_skills",
        sa.Column(
            "profile_id",
            sa.UUID(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "skill_id",
            sa.UUID(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("proficiency", sa.String(20), server_default="intermediate"),
    )

    op.create_table(
        "opportunities",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("company_logo", sa.Text(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote", sa.Boolean(), server_default="false"),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(3), server_default="USD"),
        sa.Column("posted_date", sa.Date(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("apply_url", sa.Text(), nullable=True),
        sa.Column("company_size", sa.String(50), nullable=True),
        sa.Column("skills_required", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_opportunities_user_id", "opportunities", ["user_id"])
    op.create_index("idx_opportunities_type", "opportunities", ["type"])
    op.create_index("idx_opportunities_deadline", "opportunities", ["deadline"])

    op.create_table(
        "match_scores",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "opportunity_id",
            sa.UUID(),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.DECIMAL(5, 2), nullable=False),
        sa.Column("skill_score", sa.DECIMAL(5, 2), nullable=True),
        sa.Column("location_score", sa.DECIMAL(5, 2), nullable=True),
        sa.Column("experience_score", sa.DECIMAL(5, 2), nullable=True),
        sa.Column("company_score", sa.DECIMAL(5, 2), nullable=True),
        sa.Column("reasons", sa.JSON(), server_default="[]"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("opportunity_id", "user_id"),
    )

    op.create_table(
        "applications",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            sa.UUID(),
            sa.ForeignKey("opportunities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage",
            sa.Enum(name="application_stage", create_type=False),
            server_default="saved",
        ),
        sa.Column("applied_date", sa.Date(), nullable=True),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("next_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resume_version", sa.Text(), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_applications_user_id", "applications", ["user_id"])
    op.create_index("idx_applications_stage", "applications", ["stage"])

    op.create_table(
        "contacts",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="contact_status", create_type=False),
            server_default="new",
        ),
        sa.Column("last_contact", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_contacts_user_id", "contacts", ["user_id"])
    op.create_index("idx_contacts_status", "contacts", ["status"])

    op.create_table(
        "agent_tasks",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_type", sa.Enum(name="agent_type", create_type=False), nullable=False
        ),
        sa.Column("goal_id", sa.UUID(), nullable=True),
        sa.Column("input", sa.JSON(), server_default="{}"),
        sa.Column("output", sa.JSON(), server_default="{}"),
        sa.Column(
            "status",
            sa.Enum(name="task_status", create_type=False),
            server_default="queued",
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_agent_tasks_user_id", "agent_tasks", ["user_id"])
    op.create_index("idx_agent_tasks_status", "agent_tasks", ["status"])

    op.create_table(
        "planner_goals",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("goal_text", sa.Text(), nullable=False),
        sa.Column("plan", sa.JSON(), server_default="[]"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "memory_entries",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("weight", sa.DECIMAL(3, 2), server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_memory_entries_user_id", "memory_entries", ["user_id"])

    op.create_table(
        "alert_configs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("keywords", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("locations", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("opportunity_types", sa.ARRAY(sa.String()), server_default="{}"),
        sa.Column("min_match_score", sa.Integer(), server_default="80"),
        sa.Column("frequency", sa.String(20), server_default="daily"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("idx_alert_configs_user_id", "alert_configs", ["user_id"])


def downgrade() -> None:
    """Drop all AgentForge schema."""
    op.execute("DROP TABLE IF EXISTS alert_configs CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS planner_goals CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS contacts CASCADE")
    op.execute("DROP TABLE IF EXISTS applications CASCADE")
    op.execute("DROP TABLE IF EXISTS match_scores CASCADE")
    op.execute("DROP TABLE IF EXISTS opportunities CASCADE")
    op.execute("DROP TABLE IF EXISTS profile_skills CASCADE")
    op.execute("DROP TABLE IF EXISTS skills CASCADE")
    op.execute("DROP TABLE IF EXISTS profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    op.execute("DROP TYPE IF EXISTS application_stage")
    op.execute("DROP TYPE IF EXISTS contact_status")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS agent_type")
