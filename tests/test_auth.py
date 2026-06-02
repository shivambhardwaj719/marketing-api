from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_facebook_login_returns_oauth_url(client: AsyncClient):
    response = await client.get("/api/v1/auth/facebook/login")
    assert response.status_code == 200
    data = response.json()
    assert "oauth_url" in data
    assert "facebook.com" in data["oauth_url"]
    assert "state" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, auth_headers: dict, test_user):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)


@pytest.mark.asyncio
async def test_refresh_tokens_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_refresh_tokens_valid(client: AsyncClient, test_user):
    from app.core.security import create_refresh_token
    refresh = create_refresh_token(str(test_user.id))
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
