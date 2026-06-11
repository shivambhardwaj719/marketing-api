from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from app.api.deps import CurrentUser, DBSession
from app.schemas.base import PaginatedResponse
from app.schemas.campaign import (
    AdsetResponse,
    CampaignCreate,
    CampaignInsightsResponse,
    CampaignResponse,
    CampaignUpdate,
)
from app.services.campaign import CampaignService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.get("", response_model=PaginatedResponse, summary="List campaigns")
async def list_campaigns(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="ACTIVE | PAUSED | ARCHIVED"),
):
    """List all campaigns for the authenticated user. Paginated."""
    service = CampaignService(db)
    items, total = await service.list_campaigns(
        current_user.id,
        offset=(page - 1) * page_size,
        limit=page_size,
        status=status,
    )
    return PaginatedResponse.build(
        items=[CampaignResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/sync/{ad_account_id}",
    response_model=list[CampaignResponse],
    summary="Sync campaigns from Facebook",
)
async def sync_campaigns(
    ad_account_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Pull latest campaigns from the Facebook Marketing API and upsert into DB."""
    service = CampaignService(db)
    campaigns = await service.sync_campaigns(current_user.id, ad_account_id)
    return [CampaignResponse.model_validate(c) for c in campaigns]


@router.post("", response_model=CampaignResponse, status_code=201, summary="Create campaign")
async def create_campaign(
    body: CampaignCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Create a new campaign on Facebook and store it locally."""
    service = CampaignService(db)
    platform = "instagram" if "instagram" in body.publisher_platforms else "facebook"
    campaign = await service.create_campaign(
        current_user.id, 
        body,
        platform=platform,
        publisher_platforms=body.publisher_platforms,
        instagram_positions=body.instagram_positions,
        facebook_positions=body.facebook_positions
    )
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse, summary="Get campaign")
async def get_campaign(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get a single campaign by its database UUID."""
    from app.repositories.campaign import CampaignRepository
    repo = CampaignRepository(db)
    campaign = await repo.get_by_user_and_id(current_user.id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse, summary="Update campaign")
async def update_campaign(
    campaign_id: uuid.UUID,
    body: CampaignUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update campaign name, status, or budget."""
    service = CampaignService(db)
    campaign = await service.update_campaign(current_user.id, campaign_id, body)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignResponse, summary="Pause campaign")
async def pause_campaign(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Set campaign status to PAUSED on Facebook."""
    service = CampaignService(db)
    campaign = await service.pause_campaign(current_user.id, campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignResponse, summary="Resume campaign")
async def resume_campaign(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Set campaign status to ACTIVE on Facebook."""
    service = CampaignService(db)
    campaign = await service.resume_campaign(current_user.id, campaign_id)
    return CampaignResponse.model_validate(campaign)


@router.get(
    "/{campaign_id}/insights",
    response_model=CampaignInsightsResponse,
    summary="Get campaign insights",
)
async def get_campaign_insights(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    date_preset: str = Query(
        "last_30d",
        description="last_7d | last_14d | last_30d | last_90d",
    ),
):
    """Fetch campaign performance metrics from the Facebook Insights API."""
    service = CampaignService(db)
    return await service.get_campaign_insights(current_user.id, campaign_id, date_preset)


@router.post(
    "/{campaign_id}/sync-adsets",
    response_model=list[AdsetResponse],
    summary="Sync ad sets for a campaign",
)
async def sync_adsets(
    campaign_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Pull ad sets from Facebook for a campaign and upsert into DB."""
    service = CampaignService(db)
    adsets = await service.sync_adsets(current_user.id, campaign_id)
    return [AdsetResponse.model_validate(a) for a in adsets]

# ─── Adset Endpoints ──────────────────────────────────────────────────────────

@router.patch("/adsets/{adset_id}", response_model=AdsetResponse, summary="Update adset")
async def update_adset(
    adset_id: uuid.UUID,
    body: dict[str, Any],
    current_user: CurrentUser,
    db: DBSession,
):
    service = CampaignService(db)
    adset = await service.update_adset(current_user.id, adset_id, body)
    return AdsetResponse.model_validate(adset)

@router.get("/adsets/{adset_id}/insights", summary="Get adset insights")
async def get_adset_insights(
    adset_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    date_preset: str = Query("last_30d"),
):
    service = CampaignService(db)
    return await service.get_adset_insights(current_user.id, adset_id, date_preset)

@router.post("/adsets/{adset_id}/sync-ads", summary="Sync ads for an adset")
async def sync_ads(
    adset_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = CampaignService(db)
    ads = await service.sync_ads(current_user.id, adset_id)
    # We don't have AdResponse strictly required here but returning raw dicts for now
    return {"synced_count": len(ads)}

# ─── Ad Endpoints ─────────────────────────────────────────────────────────────

@router.patch("/ads/{ad_id}", summary="Update ad")
async def update_ad(
    ad_id: uuid.UUID,
    body: dict[str, Any],
    current_user: CurrentUser,
    db: DBSession,
):
    service = CampaignService(db)
    ad = await service.update_ad(current_user.id, ad_id, body)
    return {"status": "success", "ad_id": str(ad.id)}

@router.get("/ads/{ad_id}/insights", summary="Get ad insights")
async def get_ad_insights(
    ad_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    date_preset: str = Query("last_30d"),
):
    service = CampaignService(db)
    return await service.get_ad_insights(current_user.id, ad_id, date_preset)
