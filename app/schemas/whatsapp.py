from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class WhatsAppContactBase(BaseModel):
    full_name: str
    country_code: str
    mobile_number: str
    gender: str | None = None
    email: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    notes: str | None = None

class WhatsAppContactCreate(WhatsAppContactBase):
    pass

class WhatsAppContactUpdate(WhatsAppContactBase):
    full_name: str | None = None
    country_code: str | None = None
    mobile_number: str | None = None

class WhatsAppContactResponse(WhatsAppContactBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class WhatsAppTemplateBase(BaseModel):
    template_name: str
    category: str
    language: str = "en_US"
    header_type: str | None = None
    header_content: str | None = None
    body: str
    footer: str | None = None
    buttons: list[dict[str, Any]] | None = None
    variables: list[str] | None = None

class WhatsAppTemplateCreate(WhatsAppTemplateBase):
    pass

class WhatsAppTemplateUpdate(WhatsAppTemplateBase):
    pass

class WhatsAppTemplateResponse(WhatsAppTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class WhatsAppCampaignBase(BaseModel):
    campaign_name: str
    description: str | None = None
    campaign_type: str
    template_id: UUID
    scheduled_at: datetime | None = None

class WhatsAppCampaignCreate(WhatsAppCampaignBase):
    contact_ids: list[UUID]

class WhatsAppCampaignResponse(WhatsAppCampaignBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

class WhatsAppMessageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    campaign_id: UUID | None = None
    contact_id: UUID | None = None
    template_id: UUID | None = None
    status: str
    response: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
