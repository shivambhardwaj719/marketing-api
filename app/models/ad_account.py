from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.facebook_account import FacebookAccount


class AdAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "ad_accounts"

    facebook_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facebook_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_status: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    facebook_account: Mapped[FacebookAccount] = relationship(
        "FacebookAccount", back_populates="ad_accounts"
    )
    campaigns: Mapped[list[Campaign]] = relationship(
        "Campaign", back_populates="ad_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AdAccount id={self.account_id} name={self.account_name}>"
