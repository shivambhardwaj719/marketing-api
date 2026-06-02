from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import get_logger
from app.core.security import decrypt_token
from app.integrations.facebook.client import FacebookGraphClient
from app.models.ad_account import AdAccount
from app.models.adset import Adset
from app.models.campaign import Campaign
from app.repositories.campaign import CampaignRepository
from app.schemas.campaign import CampaignCreate, CampaignInsightsResponse, CampaignUpdate

logger = get_logger(__name__)


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.campaign_repo = CampaignRepository(session)

    async def _get_account_token(self, user_id: uuid.UUID, ad_account_id: uuid.UUID) -> tuple[AdAccount, str]:
        result = await self.session.execute(
            select(AdAccount).where(
                AdAccount.id == ad_account_id,
                AdAccount.user_id == user_id,
                AdAccount.is_active.is_(True),
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise NotFoundError("Ad account not found")

        from app.models.facebook_account import FacebookAccount
        fb_result = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.id == account.facebook_account_id)
        )
        fb_account = fb_result.scalar_one_or_none()
        if not fb_account:
            raise NotFoundError("Facebook account not found")

        token = decrypt_token(fb_account.long_lived_token_encrypted or fb_account.access_token_encrypted)
        return account, token

    async def sync_campaigns(self, user_id: uuid.UUID, ad_account_id: uuid.UUID) -> list[Campaign]:
        account, token = await self._get_account_token(user_id, ad_account_id)

        async with FacebookGraphClient(token) as client:
            campaigns_data = await client.get_campaigns(account.account_id)

        synced: list[Campaign] = []
        for c in campaigns_data:
            existing = await self.campaign_repo.get_by_campaign_id(c["id"])
            if not existing:
                campaign = Campaign(
                    ad_account_id=ad_account_id,
                    user_id=user_id,
                    campaign_id=c["id"],
                    name=c.get("name", ""),
                    objective=c.get("objective"),
                    status=c.get("status", "PAUSED"),
                    effective_status=c.get("effective_status"),
                    daily_budget=int(c["daily_budget"]) if c.get("daily_budget") is not None else None,
                    lifetime_budget=int(c["lifetime_budget"]) if c.get("lifetime_budget") is not None else None,
                    start_time=c.get("start_time"),
                    stop_time=c.get("stop_time"),
                )
                self.session.add(campaign)
                synced.append(campaign)
            else:
                await self.campaign_repo.update(
                    existing,
                    {
                        "name": c.get("name", existing.name),
                        "status": c.get("status", existing.status),
                        "effective_status": c.get("effective_status"),
                        "daily_budget": int(c["daily_budget"]) if c.get("daily_budget") is not None else existing.daily_budget,
                        "lifetime_budget": int(c["lifetime_budget"]) if c.get("lifetime_budget") is not None else existing.lifetime_budget,
                    },
                )
                synced.append(existing)

        await self.session.flush()
        return synced

    async def create_campaign(
        self, 
        user_id: uuid.UUID, 
        data: CampaignCreate,
        platform: str = "facebook",
        publisher_platforms: list[str] | None = None,
        instagram_positions: list[str] | None = None,
        facebook_positions: list[str] | None = None
    ) -> Campaign:
        account, token = await self._get_account_token(user_id, data.ad_account_id)

        payload: dict[str, Any] = {
            "name": data.name,
            "objective": data.objective,
            "status": data.status,
            "special_ad_categories": [],
        }
        if data.daily_budget:
            payload["daily_budget"] = data.daily_budget
        elif data.lifetime_budget:
            payload["lifetime_budget"] = data.lifetime_budget
        if data.start_time:
            payload["start_time"] = data.start_time
        if data.stop_time:
            payload["stop_time"] = data.stop_time

        async with FacebookGraphClient(token) as client:
            result = await client.create_campaign(account.account_id, payload)

        campaign = Campaign(
            ad_account_id=data.ad_account_id,
            user_id=user_id,
            campaign_id=result["id"],
            name=data.name,
            objective=data.objective,
            status=data.status,
            platform=platform,
            daily_budget=data.daily_budget,
            lifetime_budget=data.lifetime_budget,
            start_time=data.start_time,
            stop_time=data.stop_time,
            publisher_platforms=publisher_platforms,
            instagram_positions=instagram_positions,
            facebook_positions=facebook_positions,
        )
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        logger.info("campaign_created", campaign_id=campaign.id)

        # Auto-create the initial adset for the campaign
        try:
            await self.create_adset(
                user_id=user_id,
                ad_account_db_id=data.ad_account_id,
                campaign_db_id=campaign.id,
                name=f"{data.name} - Adset",
                daily_budget=data.daily_budget,
                publisher_platforms=publisher_platforms or ["facebook"],
                instagram_positions=instagram_positions or ["stream", "story"],
                facebook_positions=facebook_positions or ["feed", "story"]
            )
        except Exception as e:
            logger.error("failed_to_auto_create_adset", error=str(e))

        return campaign

    async def create_adset(
        self,
        user_id: uuid.UUID,
        ad_account_db_id: uuid.UUID,
        campaign_db_id: uuid.UUID,
        name: str,
        daily_budget: int | None,
        publisher_platforms: list[str] = ["facebook"],
        instagram_positions: list[str] = ["stream", "story"],
        facebook_positions: list[str] = ["feed", "story"]
    ):
        account, token = await self._get_account_token(user_id, ad_account_db_id)
        
        # Get campaign
        res = await self.session.execute(
            select(Campaign).where(Campaign.id == campaign_db_id)
        )
        campaign = res.scalar_one_or_none()
        if not campaign:
            raise NotFoundError("Campaign not found")

        # Targeting spec
        targeting: dict[str, Any] = {
            "geo_locations": {"countries": ["US"]},
            "publisher_platforms": publisher_platforms,
        }
        if "instagram" in publisher_platforms:
            targeting["instagram_positions"] = instagram_positions
        if "facebook" in publisher_platforms:
            targeting["facebook_positions"] = facebook_positions

        payload: dict[str, Any] = {
            "name": name,
            "campaign_id": campaign.campaign_id,
            "status": "PAUSED",
            "targeting": targeting,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "REACH",  # Fallback
            "bid_amount": 200,
        }
        if daily_budget:
            payload["daily_budget"] = daily_budget

        # If campaign objective is LEAD_GENERATION, optimization_goal usually needs to be LEAD_GENERATION
        if campaign.objective in ("OUTCOME_LEADS", "LEAD_GENERATION"):
            payload["optimization_goal"] = "LEAD_GENERATION"

        async with FacebookGraphClient(token) as client:
            result = await client.create_adset(account.account_id, payload)
        
        from app.models.adset import Adset
        adset = Adset(
            campaign_id=campaign.id,
            user_id=user_id,
            adset_id=result["id"],
            name=name,
            status="PAUSED",
            effective_status="PAUSED",
            daily_budget=daily_budget,
            targeting=targeting,
        )
        self.session.add(adset)
        await self.session.commit()
        await self.session.refresh(adset)
        return adset

    async def create_ad(
        self,
        user_id: uuid.UUID,
        ad_account_db_id: uuid.UUID,
        adset_db_id: uuid.UUID,
        name: str,
        creative_id: str
    ):
        account, token = await self._get_account_token(user_id, ad_account_db_id)

        from app.models.adset import Adset
        res = await self.session.execute(
            select(Adset).where(Adset.id == adset_db_id)
        )
        adset = res.scalar_one_or_none()
        if not adset:
            raise NotFoundError("Adset not found")

        payload: dict[str, Any] = {
            "name": name,
            "adset_id": adset.adset_id,
            "status": "PAUSED",
            "creative": {"creative_id": creative_id},
        }

        async with FacebookGraphClient(token) as client:
            result = await client.create_ad(account.account_id, payload)

        from app.models.ad import Ad
        ad = Ad(
            adset_id=adset.id,
            user_id=user_id,
            ad_id=result["id"],
            name=name,
            status="PAUSED",
            effective_status="PAUSED",
        )
        self.session.add(ad)
        await self.session.commit()
        await self.session.refresh(ad)
        return ad

    async def update_campaign(
        self, user_id: uuid.UUID, campaign_db_id: uuid.UUID, data: CampaignUpdate
    ) -> Campaign:
        campaign = await self.campaign_repo.get_by_user_and_id(user_id, campaign_db_id)
        if not campaign:
            raise NotFoundError("Campaign not found")

        ad_account = await self.session.get(AdAccount, campaign.ad_account_id)
        if not ad_account:
            raise NotFoundError("Ad account not found")

        from app.models.facebook_account import FacebookAccount
        fb_result = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.id == ad_account.facebook_account_id)
        )
        fb_account = fb_result.scalar_one_or_none()
        token = decrypt_token(fb_account.access_token_encrypted)

        payload = data.model_dump(exclude_none=True)
        if "daily_budget" in payload and "lifetime_budget" in payload:
            del payload["lifetime_budget"]
            
        if payload:
            async with FacebookGraphClient(token) as client:
                await client.update_campaign(campaign.campaign_id, payload)

        await self.campaign_repo.update(campaign, payload)
        return campaign

    async def pause_campaign(self, user_id: uuid.UUID, campaign_db_id: uuid.UUID) -> Campaign:
        return await self.update_campaign(
            user_id, campaign_db_id, CampaignUpdate(status="PAUSED")
        )

    async def resume_campaign(self, user_id: uuid.UUID, campaign_db_id: uuid.UUID) -> Campaign:
        return await self.update_campaign(
            user_id, campaign_db_id, CampaignUpdate(status="ACTIVE")
        )

    async def get_campaign_insights(
        self, user_id: uuid.UUID, campaign_db_id: uuid.UUID, date_preset: str = "last_30d"
    ) -> CampaignInsightsResponse:
        campaign = await self.campaign_repo.get_by_user_and_id(user_id, campaign_db_id)
        if not campaign:
            raise NotFoundError("Campaign not found")

        ad_account = await self.session.get(AdAccount, campaign.ad_account_id)
        from app.models.facebook_account import FacebookAccount
        fb_result = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.id == ad_account.facebook_account_id)
        )
        fb_account = fb_result.scalar_one_or_none()
        token = decrypt_token(fb_account.access_token_encrypted)

        async with FacebookGraphClient(token) as client:
            insights = await client.get_campaign_insights(campaign.campaign_id, date_preset=date_preset)

        # Extract CPL from actions
        leads_count = None
        cpl = None
        for action in insights.get("actions", []):
            if action.get("action_type") == "lead":
                leads_count = action.get("value")
        for cpa in insights.get("cost_per_action_type", []):
            if cpa.get("action_type") == "lead":
                cpl = cpa.get("value")

        return CampaignInsightsResponse(
            campaign_id=campaign.campaign_id,
            campaign_name=campaign.name,
            impressions=insights.get("impressions"),
            clicks=insights.get("clicks"),
            spend=insights.get("spend"),
            reach=insights.get("reach"),
            cpm=insights.get("cpm"),
            cpc=insights.get("cpc"),
            ctr=insights.get("ctr"),
            leads=leads_count,
            cost_per_lead=cpl,
            date_start=insights.get("date_start"),
            date_stop=insights.get("date_stop"),
        )

    async def sync_adsets(self, user_id: uuid.UUID, campaign_db_id: uuid.UUID) -> list[Adset]:
        campaign = await self.campaign_repo.get_by_user_and_id(user_id, campaign_db_id)
        if not campaign:
            raise NotFoundError("Campaign not found")

        ad_account = await self.session.get(AdAccount, campaign.ad_account_id)
        from app.models.facebook_account import FacebookAccount
        fb_result = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.id == ad_account.facebook_account_id)
        )
        fb_account = fb_result.scalar_one_or_none()
        token = decrypt_token(fb_account.access_token_encrypted)

        async with FacebookGraphClient(token) as client:
            adsets_data = await client.get_adsets(campaign.campaign_id)

        synced: list[Adset] = []
        for a in adsets_data:
            result = await self.session.execute(
                select(Adset).where(Adset.adset_id == a["id"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                adset = Adset(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    adset_id=a["id"],
                    name=a.get("name", ""),
                    status=a.get("status", "PAUSED"),
                    effective_status=a.get("effective_status"),
                    daily_budget=a.get("daily_budget"),
                    lifetime_budget=a.get("lifetime_budget"),
                    bid_amount=a.get("bid_amount"),
                    optimization_goal=a.get("optimization_goal"),
                    billing_event=a.get("billing_event"),
                    targeting=a.get("targeting"),
                )
                self.session.add(adset)
                synced.append(adset)
            else:
                existing.status = a.get("status", existing.status)
                synced.append(existing)

        await self.session.flush()
        return synced

    async def list_campaigns(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[Campaign], int]:
        items = await self.campaign_repo.get_by_user(
            user_id, offset=offset, limit=limit, status=status
        )
        total = await self.campaign_repo.count_by_user(user_id)
        return items, total

    async def update_adset(self, user_id: uuid.UUID, adset_db_id: uuid.UUID, data: dict[str, Any]) -> Adset:
        from app.models.adset import Adset
        res = await self.session.execute(select(Adset).where(Adset.id == adset_db_id))
        adset = res.scalar_one_or_none()
        if not adset:
            raise NotFoundError("Adset not found")

        campaign = await self.session.get(Campaign, adset.campaign_id)
        account, token = await self._get_account_token(user_id, campaign.ad_account_id)

        if data:
            async with FacebookGraphClient(token) as client:
                await client.update_adset(adset.adset_id, data)

        for key, value in data.items():
            setattr(adset, key, value)
        await self.session.flush()
        return adset

    async def get_adset_insights(self, user_id: uuid.UUID, adset_db_id: uuid.UUID, date_preset: str = "last_30d") -> dict[str, Any]:
        from app.models.adset import Adset
        res = await self.session.execute(select(Adset).where(Adset.id == adset_db_id))
        adset = res.scalar_one_or_none()
        if not adset:
            raise NotFoundError("Adset not found")

        campaign = await self.session.get(Campaign, adset.campaign_id)
        account, token = await self._get_account_token(user_id, campaign.ad_account_id)

        async with FacebookGraphClient(token) as client:
            insights = await client.get_adset_insights(adset.adset_id, date_preset=date_preset)
        return insights

    async def sync_ads(self, user_id: uuid.UUID, adset_db_id: uuid.UUID) -> list[Any]:
        from app.models.adset import Adset
        from app.models.ad import Ad
        
        res = await self.session.execute(select(Adset).where(Adset.id == adset_db_id))
        adset = res.scalar_one_or_none()
        if not adset:
            raise NotFoundError("Adset not found")

        campaign = await self.session.get(Campaign, adset.campaign_id)
        account, token = await self._get_account_token(user_id, campaign.ad_account_id)

        async with FacebookGraphClient(token) as client:
            ads_data = await client.get_ads(adset.adset_id)

        synced = []
        for a in ads_data:
            result = await self.session.execute(select(Ad).where(Ad.ad_id == a["id"]))
            existing = result.scalar_one_or_none()
            if not existing:
                ad = Ad(
                    adset_id=adset.id,
                    user_id=user_id,
                    ad_id=a["id"],
                    name=a.get("name", ""),
                    status=a.get("status", "PAUSED"),
                    effective_status=a.get("effective_status"),
                )
                self.session.add(ad)
                synced.append(ad)
            else:
                existing.status = a.get("status", existing.status)
                synced.append(existing)

        await self.session.flush()
        return synced

    async def update_ad(self, user_id: uuid.UUID, ad_db_id: uuid.UUID, data: dict[str, Any]) -> Any:
        from app.models.ad import Ad
        res = await self.session.execute(select(Ad).where(Ad.id == ad_db_id))
        ad = res.scalar_one_or_none()
        if not ad:
            raise NotFoundError("Ad not found")

        from app.models.adset import Adset
        adset = await self.session.get(Adset, ad.adset_id)
        campaign = await self.session.get(Campaign, adset.campaign_id)
        account, token = await self._get_account_token(user_id, campaign.ad_account_id)

        if data:
            async with FacebookGraphClient(token) as client:
                await client.update_ad(ad.ad_id, data)

        for key, value in data.items():
            setattr(ad, key, value)
        await self.session.flush()
        return ad

    async def get_ad_insights(self, user_id: uuid.UUID, ad_db_id: uuid.UUID, date_preset: str = "last_30d") -> dict[str, Any]:
        from app.models.ad import Ad
        res = await self.session.execute(select(Ad).where(Ad.id == ad_db_id))
        ad = res.scalar_one_or_none()
        if not ad:
            raise NotFoundError("Ad not found")

        from app.models.adset import Adset
        adset = await self.session.get(Adset, ad.adset_id)
        campaign = await self.session.get(Campaign, adset.campaign_id)
        account, token = await self._get_account_token(user_id, campaign.ad_account_id)

        async with FacebookGraphClient(token) as client:
            insights = await client.get_ad_insights(ad.ad_id, date_preset=date_preset)
        return insights
