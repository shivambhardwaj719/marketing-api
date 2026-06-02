from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class DateRangeFilter(BaseSchema):
    date_from: date | None = None
    date_to: date | None = None
    campaign_id: uuid.UUID | None = None
    page_id: uuid.UUID | None = None
    ad_account_id: uuid.UUID | None = None


class LeadCountResponse(BaseSchema):
    total: int
    new: int
    contacted: int
    qualified: int
    converted: int
    lost: int


class CampaignPerformanceItem(BaseSchema):
    campaign_id: str
    campaign_name: str
    lead_count: int
    spend: float | None = None
    impressions: int | None = None
    clicks: int | None = None
    cpl: float | None = None
    ctr: float | None = None


class DailyLeadStats(BaseSchema):
    date: str
    count: int


class DashboardResponse(BaseSchema):
    total_leads: int
    leads_today: int
    leads_this_week: int
    leads_this_month: int
    total_campaigns: int
    active_campaigns: int
    total_pages: int
    total_ad_accounts: int
    lead_status_breakdown: LeadCountResponse
    top_campaigns: list[CampaignPerformanceItem]
    daily_leads: list[DailyLeadStats]


class CPLResponse(BaseSchema):
    campaign_id: str
    campaign_name: str
    total_spend: float
    total_leads: int
    cost_per_lead: float
    currency: str | None
