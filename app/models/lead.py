from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ad import Ad
    from app.models.adset import Adset
    from app.models.campaign import Campaign
    from app.models.facebook_page import FacebookPage
    from app.models.form import LeadForm
    from app.models.instagram_account import InstagramAccount


class Lead(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "leads"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    adset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("adsets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ad_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    form_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facebook_pages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    instagram_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instagram_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Facebook identifiers (raw IDs from Graph API)
    facebook_lead_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    facebook_campaign_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facebook_adset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facebook_ad_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facebook_form_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    facebook_page_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Lead data
    field_data: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    placement: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_organic: Mapped[bool | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False, index=True)

    # Contact info extracted
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    campaign: Mapped[Campaign | None] = relationship("Campaign", back_populates="leads")
    adset: Mapped[Adset | None] = relationship("Adset", back_populates="leads")
    ad: Mapped[Ad | None] = relationship("Ad", back_populates="leads")
    form: Mapped[LeadForm | None] = relationship("LeadForm", back_populates="leads")
    page: Mapped[FacebookPage | None] = relationship("FacebookPage", back_populates="leads")
    instagram_account: Mapped[InstagramAccount | None] = relationship("InstagramAccount", back_populates="leads")

    def __repr__(self) -> str:
        return f"<Lead id={self.facebook_lead_id}>"
