"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("profile_picture", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "facebook_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facebook_user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("profile_picture", sa.Text(), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("long_lived_token_encrypted", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facebook_accounts_id", "facebook_accounts", ["id"])
    op.create_index("ix_facebook_accounts_user_id", "facebook_accounts", ["user_id"])
    op.create_index("ix_facebook_accounts_facebook_user_id", "facebook_accounts", ["facebook_user_id"], unique=True)

    op.create_table(
        "facebook_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facebook_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("picture_url", sa.Text(), nullable=True),
        sa.Column("page_access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("webhook_subscribed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facebook_account_id"], ["facebook_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facebook_pages_id", "facebook_pages", ["id"])
    op.create_index("ix_facebook_pages_page_id", "facebook_pages", ["page_id"])
    op.create_index("ix_facebook_pages_user_id", "facebook_pages", ["user_id"])

    op.create_table(
        "ad_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facebook_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", sa.String(64), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("account_status", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facebook_account_id"], ["facebook_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_accounts_id", "ad_accounts", ["id"])
    op.create_index("ix_ad_accounts_account_id", "ad_accounts", ["account_id"])
    op.create_index("ix_ad_accounts_user_id", "ad_accounts", ["user_id"])

    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("objective", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PAUSED"),
        sa.Column("effective_status", sa.String(32), nullable=True),
        sa.Column("daily_budget", sa.BigInteger(), nullable=True),
        sa.Column("lifetime_budget", sa.BigInteger(), nullable=True),
        sa.Column("start_time", sa.String(64), nullable=True),
        sa.Column("stop_time", sa.String(64), nullable=True),
        sa.Column("insights", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ad_account_id"], ["ad_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_campaigns_id", "campaigns", ["id"])
    op.create_index("ix_campaigns_campaign_id", "campaigns", ["campaign_id"])
    op.create_index("ix_campaigns_user_id", "campaigns", ["user_id"])

    op.create_table(
        "adsets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adset_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PAUSED"),
        sa.Column("effective_status", sa.String(32), nullable=True),
        sa.Column("daily_budget", sa.BigInteger(), nullable=True),
        sa.Column("lifetime_budget", sa.BigInteger(), nullable=True),
        sa.Column("bid_amount", sa.BigInteger(), nullable=True),
        sa.Column("optimization_goal", sa.String(64), nullable=True),
        sa.Column("billing_event", sa.String(64), nullable=True),
        sa.Column("targeting", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adsets_id", "adsets", ["id"])
    op.create_index("ix_adsets_adset_id", "adsets", ["adset_id"])

    op.create_table(
        "ads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("adset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ad_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PAUSED"),
        sa.Column("effective_status", sa.String(32), nullable=True),
        sa.Column("creative", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["adset_id"], ["adsets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ads_id", "ads", ["id"])
    op.create_index("ix_ads_ad_id", "ads", ["ad_id"])

    op.create_table(
        "forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("form_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("locale", sa.String(16), nullable=True),
        sa.Column("follow_up_action_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["page_id"], ["facebook_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forms_id", "forms", ["id"])
    op.create_index("ix_forms_form_id", "forms", ["form_id"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("adset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("form_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("facebook_lead_id", sa.String(64), nullable=False),
        sa.Column("facebook_campaign_id", sa.String(64), nullable=True),
        sa.Column("facebook_adset_id", sa.String(64), nullable=True),
        sa.Column("facebook_ad_id", sa.String(64), nullable=True),
        sa.Column("facebook_form_id", sa.String(64), nullable=True),
        sa.Column("facebook_page_id", sa.String(64), nullable=True),
        sa.Column("field_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("platform", sa.String(32), nullable=True),
        sa.Column("is_organic", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["adset_id"], ["adsets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ad_id"], ["ads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["form_id"], ["forms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["page_id"], ["facebook_pages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leads_id", "leads", ["id"])
    op.create_index("ix_leads_facebook_lead_id", "leads", ["facebook_lead_id"], unique=True)
    op.create_index("ix_leads_user_id", "leads", ["user_id"])
    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_email", "leads", ["email"])

    op.create_table(
        "webhook_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=True),
        sa.Column("facebook_object_id", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("raw_body", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_logs_id", "webhook_logs", ["id"])
    op.create_index("ix_webhook_logs_event_type", "webhook_logs", ["event_type"])
    op.create_index("ix_webhook_logs_processing_status", "webhook_logs", ["processing_status"])


def downgrade() -> None:
    op.drop_table("webhook_logs")
    op.drop_table("leads")
    op.drop_table("forms")
    op.drop_table("ads")
    op.drop_table("adsets")
    op.drop_table("campaigns")
    op.drop_table("ad_accounts")
    op.drop_table("facebook_pages")
    op.drop_table("facebook_accounts")
    op.drop_table("users")
