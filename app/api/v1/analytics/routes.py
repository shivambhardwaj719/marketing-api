from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.analytics import (
    CampaignPerformanceItem,
    DashboardResponse,
    DateRangeFilter,
    LeadCountResponse,
)
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardResponse, summary="Dashboard summary")
async def get_dashboard(current_user: CurrentUser, db: DBSession):
    """
    Full dashboard snapshot: lead counts, campaign stats, daily trend,
    top campaigns, and status breakdown.
    """
    service = AnalyticsService(db)
    return await service.get_dashboard(current_user.id)

@router.get("/leads/count", response_model=LeadCountResponse, summary="Lead count breakdown")
async def get_leads_count(
    current_user: CurrentUser,
    db: DBSession,
    date_from: date | None = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Filter to date (YYYY-MM-DD)"),
    campaign_id: uuid.UUID | None = Query(None),
    page_id: uuid.UUID | None = Query(None),
):
    """Total leads broken down by CRM status, with optional date and campaign filters."""
    service = AnalyticsService(db)
    filters = DateRangeFilter(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        page_id=page_id,
    )
    return await service.get_leads_count(current_user.id, filters)

@router.get(
    "/campaigns/performance",
    response_model=list[CampaignPerformanceItem],
    summary="Campaign performance table",
)
async def get_campaign_performance(
    current_user: CurrentUser,
    db: DBSession,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    campaign_id: uuid.UUID | None = Query(None),
    ad_account_id: uuid.UUID | None = Query(None),
):
    """Lead count per campaign with optional filters — useful for performance tables."""
    service = AnalyticsService(db)
    filters = DateRangeFilter(
        date_from=date_from,
        date_to=date_to,
        campaign_id=campaign_id,
        ad_account_id=ad_account_id,
    )
    return await service.get_campaign_performance(current_user.id, filters)
