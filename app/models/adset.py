from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ad import Ad
    from app.models.campaign import Campaign
    from app.models.lead import Lead


class Adset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "adsets"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    adset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PAUSED", nullable=False)
    effective_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    daily_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    lifetime_budget: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bid_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    optimization_goal: Mapped[str | None] = mapped_column(String(64), nullable=True)
    billing_event: Mapped[str | None] = mapped_column(String(64), nullable=True)
    targeting: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="adsets")
    ads: Mapped[list[Ad]] = relationship(
        "Ad", back_populates="adset", cascade="all, delete-orphan"
    )
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="adset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Adset id={self.adset_id} name={self.name}>"
