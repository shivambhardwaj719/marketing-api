from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_account import AdAccount
from app.models.campaign import Campaign
from app.models.facebook_account import FacebookAccount


@pytest.mark.asyncio
async def test_list_campaigns_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/campaigns", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_campaigns_with_data(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
    db: AsyncSession,
):
    fb_account = FacebookAccount(
        id=uuid.uuid4(),
        user_id=test_user.id,
        facebook_user_id="fb_user_123",
        access_token_encrypted="encrypted_token",
        is_active=True,
    )
    db.add(fb_account)
    await db.flush()

    ad_account = AdAccount(
        id=uuid.uuid4(),
        facebook_account_id=fb_account.id,
        user_id=test_user.id,
        account_id="act_123456",
        is_active=True,
    )
    db.add(ad_account)
    await db.flush()

    campaign = Campaign(
        id=uuid.uuid4(),
        ad_account_id=ad_account.id,
        user_id=test_user.id,
        campaign_id="camp_123",
        name="Test Campaign",
        status="ACTIVE",
    )
    db.add(campaign)
    await db.flush()

    response = await client.get("/api/v1/campaigns", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["campaign_id"] == "camp_123" for c in data["items"])


@pytest.mark.asyncio
async def test_pause_campaign_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        f"/api/v1/campaigns/{uuid.uuid4()}/pause",
        headers=auth_headers,
    )
    assert response.status_code == 404
