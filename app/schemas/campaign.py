from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class CampaignCreate(BaseSchema):
    ad_account_id: uuid.UUID
    name: str = Field(min_length=1, max_length=512)
    objective: str
    status: Literal["ACTIVE", "PAUSED"] = "PAUSED"
    daily_budget: int | None = Field(None, gt=0, description="In account currency cents")
    lifetime_budget: int | None = Field(None, gt=0)
    start_time: str | None = None
    stop_time: str | None = None
    publisher_platforms: list[str] = Field(default_factory=lambda: ["facebook"])
    instagram_positions: list[str] = Field(default_factory=lambda: ["stream", "story", "reels"])
    facebook_positions: list[str] = Field(default_factory=lambda: ["feed", "story", "video_feeds"])


class CampaignUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=512)
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED", "DELETED"] | None = None
    daily_budget: int | None = Field(None, gt=0)
    lifetime_budget: int | None = Field(None, gt=0)


class CampaignResponse(UUIDSchema, TimestampSchema):
    campaign_id: str
    name: str
    objective: str | None
    status: str
    effective_status: str | None
    daily_budget: int | None
    lifetime_budget: int | None
    start_time: str | None
    stop_time: str | None
    insights: dict[str, Any] | None
    publisher_platforms: list[str] | None
    instagram_positions: list[str] | None
    facebook_positions: list[str] | None


class CampaignInsightsResponse(BaseSchema):
    campaign_id: str
    campaign_name: str
    impressions: str | None = None
    clicks: str | None = None
    spend: str | None = None
    reach: str | None = None
    cpm: str | None = None
    cpc: str | None = None
    ctr: str | None = None
    leads: str | None = None
    cost_per_lead: str | None = None
    date_start: str | None = None
    date_stop: str | None = None


class AdsetResponse(UUIDSchema, TimestampSchema):
    adset_id: str
    name: str
    status: str
    effective_status: str | None
    daily_budget: int | None
    lifetime_budget: int | None
    optimization_goal: str | None


class AdResponse(UUIDSchema, TimestampSchema):
    ad_id: str
    name: str
    status: str
    effective_status: str | None

class AdsetUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=512)
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED", "DELETED"] | None = None
    daily_budget: int | None = Field(None, gt=0)
    lifetime_budget: int | None = Field(None, gt=0)

class AdCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=512)
    status: Literal["ACTIVE", "PAUSED"] = "PAUSED"
    creative: dict[str, Any]

class AdUpdate(BaseSchema):
    name: str | None = Field(None, min_length=1, max_length=512)
    status: Literal["ACTIVE", "PAUSED", "ARCHIVED", "DELETED"] | None = None
