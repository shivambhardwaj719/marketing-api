"""Add hashed_password to users

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "hashed_password")
