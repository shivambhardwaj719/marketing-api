from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ad_account import AdAccount
    from app.models.adset import Adset
    from app.models.lead import Lead


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "campaigns"

    ad_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ad_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PAUSED", nullable=False)
    effective_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    daily_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lifetime_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stop_time: Mapped[str | None] = mapped_column(String(64), nullable=True)
    insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    platform: Mapped[str] = mapped_column(String(32), default="facebook", nullable=False)
    publisher_platforms: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    instagram_positions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    facebook_positions: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    ad_account: Mapped[AdAccount] = relationship("AdAccount", back_populates="campaigns")
    adsets: Mapped[list[Adset]] = relationship(
        "Adset", back_populates="campaign", cascade="all, delete-orphan"
    )
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="campaign", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Campaign id={self.campaign_id} name={self.name}>"
