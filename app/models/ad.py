from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.adset import Adset
    from app.models.lead import Lead


class Ad(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ads"

    adset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("adsets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ad_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PAUSED", nullable=False)
    effective_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    creative: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    adset: Mapped[Adset] = relationship("Adset", back_populates="ads")
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="ad", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ad id={self.ad_id} name={self.name}>"
