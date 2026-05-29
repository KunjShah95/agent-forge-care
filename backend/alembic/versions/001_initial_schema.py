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

    # Users
    op.create_table("users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # ... (full migration in initial schema creation via models)
    pass


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
