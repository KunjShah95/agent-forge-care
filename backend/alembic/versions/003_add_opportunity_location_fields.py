"""add city, state, country, industry to opportunities

Revision ID: 003
Revises: 42f2c209e2f6
Create Date: 2026-06-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "42f2c209e2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("city", sa.String(150), nullable=True))
    op.add_column("opportunities", sa.Column("state", sa.String(100), nullable=True))
    op.add_column("opportunities", sa.Column("country", sa.String(100), nullable=True))
    op.add_column("opportunities", sa.Column("industry", sa.String(150), nullable=True))
    op.create_index("idx_opportunities_city", "opportunities", ["city"])
    op.create_index("idx_opportunities_state", "opportunities", ["state"])
    op.create_index("idx_opportunities_country", "opportunities", ["country"])
    op.create_index("idx_opportunities_industry", "opportunities", ["industry"])


def downgrade() -> None:
    op.drop_index("idx_opportunities_industry", table_name="opportunities")
    op.drop_index("idx_opportunities_country", table_name="opportunities")
    op.drop_index("idx_opportunities_state", table_name="opportunities")
    op.drop_index("idx_opportunities_city", table_name="opportunities")
    op.drop_column("opportunities", "industry")
    op.drop_column("opportunities", "country")
    op.drop_column("opportunities", "state")
    op.drop_column("opportunities", "city")
