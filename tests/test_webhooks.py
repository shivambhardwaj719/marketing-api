from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
async def test_webhook_verification_success(client: AsyncClient):
    response = await client.get(
        "/api/v1/webhooks/facebook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "test_challenge_123",
            "hub.verify_token": settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN,
        },
    )
    assert response.status_code == 200
    assert response.text == "test_challenge_123"


@pytest.mark.asyncio
async def test_webhook_verification_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/v1/webhooks/facebook",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge",
            "hub.verify_token": "wrong_token",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_receive_leadgen(client: AsyncClient):
    payload = {
        "object": "page",
        "entry": [
            {
                "id": "123456789",
                "time": 1609459200,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "987654321",
                            "form_id": "111222333",
                            "page_id": "123456789",
                            "ad_id": "444555666",
                        },
                    }
                ],
            }
        ],
    }
    response = await client.post(
        "/api/v1/webhooks/facebook",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"
