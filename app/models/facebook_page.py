from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.facebook_account import FacebookAccount
    from app.models.form import LeadForm
    from app.models.lead import Lead


class FacebookPage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "facebook_pages"

    facebook_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facebook_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    webhook_subscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    facebook_account: Mapped[FacebookAccount] = relationship(
        "FacebookAccount", back_populates="pages"
    )
    forms: Mapped[list[LeadForm]] = relationship(
        "LeadForm", back_populates="page", cascade="all, delete-orphan"
    )
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="page", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FacebookPage id={self.page_id} name={self.name}>"
