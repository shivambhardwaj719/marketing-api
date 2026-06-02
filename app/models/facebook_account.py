from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.ad_account import AdAccount
    from app.models.facebook_page import FacebookPage
    from app.models.user import User


class FacebookAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "facebook_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    facebook_user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_picture: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Encrypted tokens
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    long_lived_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="facebook_accounts")
    pages: Mapped[list[FacebookPage]] = relationship(
        "FacebookPage", back_populates="facebook_account", cascade="all, delete-orphan"
    )
    ad_accounts: Mapped[list[AdAccount]] = relationship(
        "AdAccount", back_populates="facebook_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<FacebookAccount fb_id={self.facebook_user_id}>"
