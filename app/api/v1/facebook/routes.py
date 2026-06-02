from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentUser, DBSession
from app.schemas.facebook import (
    AdAccountResponse,
    FacebookAccountResponse,
    FacebookPageResponse,
)
from app.services.facebook import FacebookService

router = APIRouter(prefix="/facebook", tags=["Facebook"])


@router.get(
    "/accounts",
    response_model=list[FacebookAccountResponse],
    summary="List connected Facebook accounts",
)
async def get_connected_accounts(current_user: CurrentUser, db: DBSession):
    """Returns all Facebook accounts linked to the authenticated user."""
    service = FacebookService(db)
    return await service.get_connected_accounts(current_user.id)


@router.get(
    "/pages",
    response_model=list[FacebookPageResponse],
    summary="Get all pages for the logged-in user",
)
async def get_all_pages(current_user: CurrentUser, db: DBSession):
    """
    Returns every Facebook Page stored in the database that belongs to the
    authenticated user, across all connected Facebook accounts.

    Run POST /facebook/pages/sync first to pull the latest pages from Facebook.
    """
    service = FacebookService(db)
    return await service.get_all_user_pages(current_user.id)


@router.post(
    "/pages/sync",
    response_model=list[FacebookPageResponse],
    summary="Sync all pages from Facebook",
)
async def sync_all_pages(current_user: CurrentUser, db: DBSession):
    """
    Fetches pages from every connected Facebook account via the Graph API,
    upserts them into the database, and returns the full updated list.
    """
    service = FacebookService(db)
    return await service.sync_all_user_pages(current_user.id)


@router.get(
    "/accounts/{fb_account_id}/pages",
    response_model=list[FacebookPageResponse],
    summary="List Facebook Pages",
)
async def get_pages(
    fb_account_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """List all synced Facebook Pages for a connected account."""
    service = FacebookService(db)
    return await service.get_pages(current_user.id, fb_account_id)


@router.post(
    "/accounts/{fb_account_id}/sync-pages",
    response_model=list[FacebookPageResponse],
    summary="Sync Facebook Pages",
)
async def sync_pages(
    fb_account_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Fetch and upsert all Facebook Pages for a connected account."""
    service = FacebookService(db)
    return await service.sync_pages(current_user.id, fb_account_id)


@router.post(
    "/accounts/{fb_account_id}/sync-ad-accounts",
    response_model=list[AdAccountResponse],
    summary="Sync Ad Accounts",
)
async def sync_ad_accounts(
    fb_account_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Fetch and upsert all Ad Accounts for a connected Facebook account."""
    service = FacebookService(db)
    return await service.sync_ad_accounts(current_user.id, fb_account_id)


@router.post(
    "/pages/{page_id}/subscribe-webhook",
    summary="Subscribe page to leadgen webhook",
)
async def subscribe_page_webhook(
    page_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Subscribe a Facebook Page to receive real-time leadgen webhook events."""
    service = FacebookService(db)
    return await service.subscribe_page_webhook(current_user.id, page_id)


@router.get(
    "/pages/{page_id}/forms",
    response_model=list[dict],
    summary="List lead gen forms for a page",
)
async def get_lead_forms(
    page_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Fetch all lead generation forms for a Facebook Page and sync them to DB."""
    service = FacebookService(db)
    return await service.get_lead_forms(current_user.id, page_id)


# ─── Business Manager Endpoints ──────────────────────────────────────────────

@router.get(
    "/accounts/{fb_account_id}/businesses",
    summary="List Facebook Businesses",
)
async def get_businesses(
    fb_account_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.get_businesses(current_user.id, fb_account_id)

@router.get(
    "/accounts/{fb_account_id}/businesses/{business_id}/ad-accounts",
    summary="List Ad Accounts owned by Business",
)
async def get_business_ad_accounts(
    fb_account_id: uuid.UUID,
    business_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.get_business_ad_accounts(current_user.id, fb_account_id, business_id)


# ─── Ad Creatives Endpoints ──────────────────────────────────────────────────

@router.get(
    "/accounts/{fb_account_id}/ad-accounts/{ad_account_fb_id}/creatives",
    summary="List Ad Creatives for an Ad Account",
)
async def get_adcreatives(
    fb_account_id: uuid.UUID,
    ad_account_fb_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.get_adcreatives(current_user.id, fb_account_id, ad_account_fb_id)

@router.post(
    "/accounts/{fb_account_id}/ad-accounts/{ad_account_fb_id}/creatives",
    summary="Create Ad Creative",
)
async def create_adcreative(
    fb_account_id: uuid.UUID,
    ad_account_fb_id: str,
    body: dict,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.create_adcreative(current_user.id, fb_account_id, ad_account_fb_id, body)

@router.post(
    "/accounts/{fb_account_id}/ad-accounts/{ad_account_fb_id}/adimages",
    summary="Upload Ad Image",
)
async def upload_adimage(
    fb_account_id: uuid.UUID,
    ad_account_fb_id: str,
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
):
    """Upload a raw image file directly to the Facebook Ad Account Media Library."""
    service = FacebookService(db)
    image_bytes = await file.read()
    account, token = await service._get_fb_account_token(current_user.id, fb_account_id)
    
    from app.integrations.facebook.client import FacebookGraphClient
    async with FacebookGraphClient(token) as client:
        return await client.upload_adimage(ad_account_fb_id, image_bytes, file.filename or "image.jpg")


# ─── Custom Audiences Endpoints ──────────────────────────────────────────────

@router.get(
    "/accounts/{fb_account_id}/ad-accounts/{ad_account_fb_id}/audiences",
    summary="List Custom Audiences for an Ad Account",
)
async def get_custom_audiences(
    fb_account_id: uuid.UUID,
    ad_account_fb_id: str,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.get_custom_audiences(current_user.id, fb_account_id, ad_account_fb_id)

@router.post(
    "/accounts/{fb_account_id}/ad-accounts/{ad_account_fb_id}/audiences",
    summary="Create Custom Audience",
)
async def create_custom_audience(
    fb_account_id: uuid.UUID,
    ad_account_fb_id: str,
    body: dict,
    current_user: CurrentUser,
    db: DBSession,
):
    service = FacebookService(db)
    return await service.create_custom_audience(current_user.id, fb_account_id, ad_account_fb_id, body)
