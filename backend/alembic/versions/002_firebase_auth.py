"""Make password_hash nullable, add firebase_uid column

Revision ID: 002
Revises: 001
Create Date: 2026-05-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", nullable=True)
    op.add_column("users", sa.Column("firebase_uid", sa.String(255), nullable=True))
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])


def downgrade() -> None:
    op.drop_index("idx_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
    op.alter_column("users", "password_hash", nullable=False)
