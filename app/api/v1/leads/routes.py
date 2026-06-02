from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DBSession
from app.schemas.base import PaginatedResponse
from app.schemas.lead import LeadFilterParams, LeadResponse, LeadStatusUpdate
from app.services.lead import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("", response_model=PaginatedResponse, summary="List leads")
async def list_leads(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    campaign_id: uuid.UUID | None = Query(None),
    adset_id: uuid.UUID | None = Query(None),
    form_id: uuid.UUID | None = Query(None),
    page_fb_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="new | contacted | qualified | converted | lost"),
    search: str | None = Query(None, description="Search by email, name or phone"),
):
    """List leads with optional filters. Paginated."""
    service = LeadService(db)
    params = LeadFilterParams(
        campaign_id=campaign_id,
        adset_id=adset_id,
        form_id=form_id,
        page_id=page_fb_id,
        status=status,
        search=search,
    )
    items, total = await service.list_leads(
        current_user.id, params, page=page, page_size=page_size
    )
    return PaginatedResponse.build(
        items=[LeadResponse.model_validate(lead) for lead in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Page-scoped endpoints (must be declared before /{lead_id} to avoid UUID clash) ──

@router.get(
    "/page/{facebook_page_id}",
    response_model=PaginatedResponse,
    summary="Get leads for a Facebook Page",
)
async def get_leads_by_page(
    facebook_page_id: str,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: str | None = Query(None, description="new | contacted | qualified | converted | lost"),
    search: str | None = Query(None, description="Search by email, name or phone"),
):

    service = LeadService(db)
    items, total = await service.list_leads_by_facebook_page(
        current_user.id,
        facebook_page_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
    )
    return PaginatedResponse.build(
        items=[LeadResponse.model_validate(lead) for lead in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/page/{facebook_page_id}/sync",
    summary="Sync leads from a Facebook Page",
)
async def sync_page_leads(
    facebook_page_id: str,
    current_user: CurrentUser,
    db: DBSession,
):

    service = LeadService(db)
    result = await service.sync_page_leads(current_user.id, facebook_page_id)
    return result


# ── Real-time SSE stream ─────────────────────────────────────────────────────

@router.get("/stream", summary="Stream real-time lead events via SSE")
async def stream_leads(current_user: CurrentUser, db: DBSession):
    """
    Server-Sent Events endpoint. Connect from the frontend to receive new leads
    pushed in real-time the moment Meta delivers them via webhook.

    Event types:
    - `connected`  — sent once when the connection is established
    - `new_lead`   — fired for every new lead captured from Meta
    - heartbeat comments (`: heartbeat`) every 25 s to keep proxies alive
    """
    import redis.asyncio as aioredis
    from app.core.config import settings

    user_id = str(current_user.id)

    async def event_generator():
        r: aioredis.Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        channel = f"leads:{user_id}"
        await pubsub.subscribe(channel)

        yield f"data: {json.dumps({'type': 'connected', 'user_id': user_id})}\n\n"

        try:
            last_heartbeat = asyncio.get_event_loop().time()
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    lead_data = json.loads(message["data"])
                    yield f"data: {json.dumps({'type': 'new_lead', 'lead': lead_data})}\n\n"
                    last_heartbeat = asyncio.get_event_loop().time()
                elif asyncio.get_event_loop().time() - last_heartbeat > 25:
                    yield ": heartbeat\n\n"
                    last_heartbeat = asyncio.get_event_loop().time()
                else:
                    await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Generic lead endpoints ───────────────────────────────────────────────────

@router.get("/{lead_id}", response_model=LeadResponse, summary="Get lead by ID")
async def get_lead(
    lead_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Get a single lead by its database UUID."""
    service = LeadService(db)
    lead = await service.get_lead(current_user.id, lead_id)
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}/status", response_model=LeadResponse, summary="Update lead status")
async def update_lead_status(
    lead_id: uuid.UUID,
    body: LeadStatusUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update a lead's CRM status: new → contacted → qualified → converted / lost."""
    service = LeadService(db)
    lead = await service.update_lead_status(current_user.id, lead_id, body.status)
    return LeadResponse.model_validate(lead)


@router.post("/fetch-form-leads", summary="Bulk import leads from a form")
async def fetch_form_leads(
    form_id: str = Query(..., description="Facebook Form ID"),
    page_id: str = Query(..., description="Facebook Page ID"),
    current_user: CurrentUser = None,
    db: DBSession = None,
):
    """Manually pull all leads from a Facebook Lead Form into the database."""
    service = LeadService(db)
    count = await service.fetch_form_leads(current_user.id, form_id, page_id)
    return {"imported": count}


@router.post("/fetch-page-leads", summary="Bulk import all leads from a Facebook Page")
async def fetch_page_leads(
    page_id: str = Query(..., description="Facebook Page ID"),
    current_user: CurrentUser = None,
    db: DBSession = None,
):
    """Manually pull all leads from all forms of a Facebook Page into the database."""
    service = LeadService(db)
    return await service.fetch_page_leads(current_user.id, page_id)


@router.post(
    "/fetch-by-asset",
    summary="Bulk import leads by asset ID and optional Business ID",
)
async def fetch_leads_by_asset(
    asset_id: str = Query(..., description="Facebook asset (Page) ID — e.g. 78765898767898"),
    business_id: str | None = Query(None, description="Facebook Business Manager ID — e.g. 9876787698787t78"),
    current_user: CurrentUser = None,
    db: DBSession = None,
):
    """
    Fetch all leads from every lead gen form associated with the given asset (Page) ID.
    If a Business Manager ID is also provided, forms from that business are included too.
    New leads are stored in the database; already-imported leads are counted as skipped.
    """
    service = LeadService(db)
    result = await service.fetch_leads_by_asset(current_user.id, asset_id, business_id)
    return result
