from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class LeadFieldData(BaseSchema):
    name: str
    values: list[str]


class LeadResponse(UUIDSchema, TimestampSchema):
    facebook_lead_id: str
    facebook_campaign_id: str | None
    facebook_adset_id: str | None
    facebook_ad_id: str | None
    facebook_form_id: str | None
    facebook_page_id: str | None
    field_data: list[dict[str, Any]] | None
    email: str | None
    phone: str | None
    full_name: str | None
    status: str
    platform: str | None
    is_organic: bool | None
    campaign_id: uuid.UUID | None
    adset_id: uuid.UUID | None
    ad_id: uuid.UUID | None
    form_id: uuid.UUID | None
    page_id: uuid.UUID | None


class LeadStatusUpdate(BaseSchema):
    status: str = Field(description="new, contacted, qualified, converted, lost")


class LeadFilterParams(BaseSchema):
    campaign_id: uuid.UUID | None = None
    adset_id: uuid.UUID | None = None
    ad_id: uuid.UUID | None = None
    form_id: uuid.UUID | None = None
    page_id: uuid.UUID | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    search: str | None = None


class LeadFormResponse(UUIDSchema, TimestampSchema):
    form_id: str
    name: str
    status: str | None
    questions: list[dict] | None
    locale: str | None
