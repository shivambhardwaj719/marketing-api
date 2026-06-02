"""add index on leads.facebook_page_id

Revision ID: a3f1c8d92e74
Revises: 6e2b633c2952
Create Date: 2026-05-27 18:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "a3f1c8d92e74"
down_revision: Union[str, None] = "6e2b633c2952"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_leads_facebook_page_id", "leads", ["facebook_page_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_facebook_page_id", table_name="leads")
