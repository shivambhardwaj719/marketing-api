from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead


@pytest.mark.asyncio
async def test_list_leads_empty(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/leads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_leads_with_data(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
    db: AsyncSession,
):
    lead = Lead(
        id=uuid.uuid4(),
        user_id=test_user.id,
        facebook_lead_id=f"fb_lead_{uuid.uuid4().hex[:8]}",
        status="new",
        email="lead@test.com",
        full_name="Lead Person",
    )
    db.add(lead)
    await db.flush()

    response = await client.get("/api/v1/leads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_lead_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get(f"/api/v1/leads/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_lead_status(
    client: AsyncClient,
    auth_headers: dict,
    test_user,
    db: AsyncSession,
):
    lead = Lead(
        id=uuid.uuid4(),
        user_id=test_user.id,
        facebook_lead_id=f"fb_lead_{uuid.uuid4().hex[:8]}",
        status="new",
    )
    db.add(lead)
    await db.flush()

    response = await client.patch(
        f"/api/v1/leads/{lead.id}/status",
        json={"status": "contacted"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "contacted"
