from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.facebook_page import FacebookPage
    from app.models.lead import Lead


class LeadForm(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "forms"

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facebook_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    form_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    locale: Mapped[str | None] = mapped_column(String(16), nullable=True)
    follow_up_action_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    page: Mapped[FacebookPage] = relationship("FacebookPage", back_populates="forms")
    leads: Mapped[list[Lead]] = relationship(
        "Lead", back_populates="form", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LeadForm id={self.form_id} name={self.name}>"
