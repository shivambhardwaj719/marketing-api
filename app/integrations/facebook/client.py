from __future__ import annotations

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.exceptions import FacebookAPIError, FacebookAuthError
from app.core.logger import get_logger

logger = get_logger(__name__)

FACEBOOK_GRAPH_BASE = settings.facebook_graph_base_url


class FacebookGraphClient:
    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> FacebookGraphClient:
        self._client = httpx.AsyncClient(
            base_url=FACEBOOK_GRAPH_BASE,
            timeout=httpx.Timeout(30.0),
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Client not started — use async with")

        query = {"access_token": self.access_token}
        if params:
            query.update(params)

        response = await self._client.request(method, path, params=query, json=json)

        try:
            data = response.json()
        except Exception:
            data = {}

        if "error" in data:
            err = data["error"]
            code = err.get("code", 0)
            msg = err.get("message", "Unknown Facebook error")
            logger.warning("facebook_api_error", code=code, message=msg, path=path)
            if code in (190, 102, 104, 2500):
                raise FacebookAuthError(msg)
            raise FacebookAPIError(msg, details=err)

        response.raise_for_status()
        return data

    async def get(self, path: str, **params: Any) -> dict[str, Any]:
        return await self._request("GET", path, params=params or None)

    async def post(self, path: str, **data: Any) -> dict[str, Any]:
        return await self._request("POST", path, json=data or None)

    # ─── Auth ──────────────────────────────────────────────────────────────────

    @classmethod
    async def exchange_code_for_token(cls, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FACEBOOK_GRAPH_BASE}/oauth/access_token",
                params={
                    "client_id": settings.FACEBOOK_APP_ID,
                    "client_secret": settings.FACEBOOK_APP_SECRET,
                    "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
                    "code": code,
                },
            )
            data = resp.json()
            if "error" in data:
                raise FacebookAuthError(data["error"].get("message", "OAuth failed"))
            return data

    @classmethod
    async def extend_token(cls, short_lived_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FACEBOOK_GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.FACEBOOK_APP_ID,
                    "client_secret": settings.FACEBOOK_APP_SECRET,
                    "fb_exchange_token": short_lived_token,
                },
            )
            data = resp.json()
            if "error" in data:
                raise FacebookAuthError(data["error"].get("message", "Token extension failed"))
            return data

    # ─── User ──────────────────────────────────────────────────────────────────

    async def get_me(self) -> dict[str, Any]:
        return await self.get("/me", fields="id,name,email,picture")

    # ─── Pages ─────────────────────────────────────────────────────────────────

    async def get_pages(self) -> list[dict[str, Any]]:
        data = await self.get("/me/accounts", fields="id,name,category,picture,access_token")
        return data.get("data", [])

    async def get_instagram_business_account(self, page_id: str) -> dict[str, Any] | None:
        data = await self.get(f"/{page_id}", fields="instagram_business_account{id,username,profile_picture_url}")
        ig_account = data.get("instagram_business_account")
        return ig_account

    # ─── Ad Accounts ───────────────────────────────────────────────────────────

    async def get_ad_accounts(self) -> list[dict[str, Any]]:
        data = await self.get(
            "/me/adaccounts",
            fields="id,name,currency,timezone_name,account_status",
        )
        return data.get("data", [])

    # ─── Businesses ────────────────────────────────────────────────────────────

    async def get_businesses(self) -> list[dict[str, Any]]:
        data = await self.get(
            "/me/businesses",
            fields="id,name,profile_picture_uri,created_time",
        )
        return data.get("data", [])

    async def get_business_ad_accounts(self, business_id: str) -> list[dict[str, Any]]:
        # Fetch both owned and client ad accounts
        owned = await self.get(
            f"/{business_id}/owned_ad_accounts",
            fields="id,name,currency,timezone_name,account_status",
        )
        client = await self.get(
            f"/{business_id}/client_ad_accounts",
            fields="id,name,currency,timezone_name,account_status",
        )
        
        accounts = []
        accounts.extend(owned.get("data", []))
        
        # Deduplicate
        seen = {acc["id"] for acc in accounts}
        for acc in client.get("data", []):
            if acc["id"] not in seen:
                accounts.append(acc)
                seen.add(acc["id"])
                
        return accounts

    # ─── Campaigns ─────────────────────────────────────────────────────────────

    async def get_campaigns(self, ad_account_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/act_{ad_account_id}/campaigns",
            fields="id,name,objective,status,effective_status,daily_budget,lifetime_budget,start_time,stop_time",
        )
        return data.get("data", [])

    async def create_campaign(
        self, ad_account_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.post(f"/act_{ad_account_id}/campaigns", **payload)

    async def update_campaign(
        self, campaign_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return await self.post(f"/{campaign_id}", **payload)

    async def get_campaign_insights(
        self,
        campaign_id: str,
        *,
        date_preset: str = "last_30d",
        fields: str | None = None,
    ) -> dict[str, Any]:
        _fields = fields or (
            "campaign_id,campaign_name,impressions,clicks,spend,reach,"
            "cpm,cpc,ctr,actions,cost_per_action_type,date_start,date_stop"
        )
        data = await self.get(
            f"/{campaign_id}/insights",
            fields=_fields,
            date_preset=date_preset,
            level="campaign",
        )
        results = data.get("data", [])
        return results[0] if results else {}

    # ─── Adsets ────────────────────────────────────────────────────────────────

    async def get_adsets(self, campaign_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/{campaign_id}/adsets",
            fields="id,name,status,effective_status,daily_budget,lifetime_budget,optimization_goal,billing_event,bid_amount,targeting",
        )
        return data.get("data", [])

    async def create_adset(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/act_{ad_account_id}/adsets", **payload)

    async def update_adset(self, adset_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/{adset_id}", **payload)

    async def get_adset_insights(self, adset_id: str, date_preset: str = "last_30d") -> dict[str, Any]:
        data = await self.get(
            f"/{adset_id}/insights",
            fields="impressions,clicks,spend,reach,cpm,cpc,ctr,actions,cost_per_action_type",
            date_preset=date_preset,
        )
        return data.get("data", [{}])[0] if data.get("data") else {}


    async def get_ads(self, adset_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/{adset_id}/ads",
            fields="id,name,status,effective_status,creative",
        )
        return data.get("data", [])

    async def create_ad(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/act_{ad_account_id}/ads", **payload)

    async def update_ad(self, ad_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/{ad_id}", **payload)

    async def get_ad_insights(self, ad_id: str, date_preset: str = "last_30d") -> dict[str, Any]:
        data = await self.get(
            f"/{ad_id}/insights",
            fields="impressions,clicks,spend,reach,cpm,cpc,ctr,actions,cost_per_action_type",
            date_preset=date_preset,
        )
        return data.get("data", [{}])[0] if data.get("data") else {}

    # ─── Ad Creatives & Images ──────────────────────────────────────────────────

    async def get_adcreatives(self, ad_account_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/act_{ad_account_id}/adcreatives",
            fields="id,name,object_story_spec,thumbnail_url,image_url,status",
        )
        return data.get("data", [])

    async def create_adcreative(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/act_{ad_account_id}/adcreatives", **payload)

    async def upload_adimage(self, ad_account_id: str, image_bytes: bytes, filename: str) -> dict[str, Any]:
        """Upload an image to the ad account's image library."""
        if self._client is None:
            raise RuntimeError("Client not started")
        
        path = f"/act_{ad_account_id}/adimages"
        query = {"access_token": self.access_token}
        files = {"filename": (filename, image_bytes, "image/jpeg")}
        
        response = await self._client.request("POST", path, params=query, files=files)
        data = response.json()
        if "error" in data:
            raise FacebookAPIError(data["error"].get("message", "Unknown error"), details=data["error"])
        
        # Facebook returns a dict with the image hash as key, or an images dict
        images = data.get("images", {})
        if images:
            return list(images.values())[0]
        return data

    # ─── Custom Audiences ───────────────────────────────────────────────────────

    async def get_custom_audiences(self, ad_account_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/act_{ad_account_id}/customaudiences",
            fields="id,name,description,customer_file_source,rule,approximate_count,time_updated",
        )
        return data.get("data", [])

    async def create_custom_audience(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/act_{ad_account_id}/customaudiences", **payload)

    async def add_users_to_audience(self, audience_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.post(f"/{audience_id}/users", **payload)

    # ─── Lead Forms ────────────────────────────────────────────────────────────

    async def get_lead_forms(self, page_id: str) -> list[dict[str, Any]]:
        data = await self.get(
            f"/{page_id}/leadgen_forms",
            fields="id,name,status,questions,locale,follow_up_action_url",
        )
        return data.get("data", [])

    async def get_business_lead_forms(self, business_id: str) -> list[dict[str, Any]]:
        """Fetch all lead gen forms under a Business Manager account."""
        data = await self.get(
            f"/{business_id}/leadgen_forms",
            fields="id,name,status,questions,locale,follow_up_action_url,page",
        )
        return data.get("data", [])

    # ─── Lead Details ──────────────────────────────────────────────────────────

    async def get_lead(self, lead_id: str) -> dict[str, Any]:
        return await self.get(
            f"/{lead_id}",
            fields="id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,is_organic,platform",
        )

    async def get_form_leads(
        self,
        form_id: str,
        *,
        after: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "fields": "id,created_time,field_data,ad_id,adset_id,campaign_id,is_organic,platform",
            "limit": limit,
        }
        if after:
            params["after"] = after
        return await self.get(f"/{form_id}/leads", **params)

    # ─── Webhooks ──────────────────────────────────────────────────────────────

    async def subscribe_page_to_app(self, page_id: str, page_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FACEBOOK_GRAPH_BASE}/{page_id}/subscribed_apps",
                params={
                    "access_token": page_token,
                    "subscribed_fields": "leadgen",
                },
            )
            return resp.json()
