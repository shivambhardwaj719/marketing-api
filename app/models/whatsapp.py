from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

class WhatsAppContact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "whatsapp_contacts"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
class WhatsAppTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "whatsapp_templates"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False) # Marketing, Utility, Authentication
    language: Mapped[str] = mapped_column(String(20), default="en_US", nullable=False)
    header_type: Mapped[str | None] = mapped_column(String(20), nullable=True) # None, Text, Image, Video, Document
    header_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    buttons: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    variables: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # PENDING, APPROVED, REJECTED

class WhatsAppCampaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "whatsapp_campaigns"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False) # Marketing, Promotional, etc.
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_templates.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", nullable=False) # DRAFT, QUEUED, PROCESSING, COMPLETED
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template: Mapped[WhatsAppTemplate] = relationship("WhatsAppTemplate")
    contacts: Mapped[list[WhatsAppCampaignContact]] = relationship("WhatsAppCampaignContact", back_populates="campaign", cascade="all, delete-orphan")

class WhatsAppCampaignContact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "whatsapp_campaign_contacts"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_contacts.id", ondelete="CASCADE"), nullable=False)
    message_status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False) # QUEUED, SENT, DELIVERED, READ, FAILED
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped[WhatsAppCampaign] = relationship("WhatsAppCampaign", back_populates="contacts")
    contact: Mapped[WhatsAppContact] = relationship("WhatsAppContact")

class WhatsAppMessageLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "whatsapp_message_logs"

    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("whatsapp_templates.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
