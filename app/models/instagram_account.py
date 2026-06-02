from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.facebook_page import FacebookPage
    from app.models.lead import Lead
    from app.models.user import User


class InstagramAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "instagram_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    facebook_page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facebook_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instagram_account_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_picture: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    access_token: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    user: Mapped[User] = relationship("User")
    facebook_page: Mapped[FacebookPage] = relationship("FacebookPage")
    leads: Mapped[list[Lead]] = relationship("Lead", back_populates="instagram_account", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<InstagramAccount username={self.username}>"
