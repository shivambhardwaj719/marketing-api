from __future__ import annotations

import asyncio
import uuid

from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.campaign_tasks.sync_all_campaigns")
def sync_all_campaigns(user_id: str) -> dict:
    """Sync all campaigns for all ad accounts of a user."""

    async def _sync():
        from app.core.database import AsyncSessionFactory
        from app.models.ad_account import AdAccount
        from app.services.campaign import CampaignService
        from sqlalchemy import select

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(AdAccount).where(
                    AdAccount.user_id == uuid.UUID(user_id),
                    AdAccount.is_active.is_(True),
                )
            )
            ad_accounts = result.scalars().all()
            service = CampaignService(session)
            total = 0
            for account in ad_accounts:
                campaigns = await service.sync_campaigns(uuid.UUID(user_id), account.id)
                total += len(campaigns)
            await session.commit()
            return total

    total = run_async(_sync())
    return {"synced": total}


@celery_app.task(name="app.workers.tasks.campaign_tasks.refresh_campaign_insights")
def refresh_campaign_insights(user_id: str) -> dict:
    """Refresh insights for all active campaigns."""

    async def _refresh():
        from app.core.database import AsyncSessionFactory
        from app.models.campaign import Campaign
        from app.services.campaign import CampaignService
        from sqlalchemy import select

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Campaign).where(
                    Campaign.user_id == uuid.UUID(user_id),
                    Campaign.status == "ACTIVE",
                )
            )
            campaigns = result.scalars().all()
            service = CampaignService(session)
            updated = 0
            for campaign in campaigns:
                try:
                    insights = await service.get_campaign_insights(
                        uuid.UUID(user_id), campaign.id
                    )
                    await session.flush()
                    updated += 1
                except Exception as e:
                    logger.warning("insight_refresh_failed", campaign_id=campaign.id, error=str(e))
            await session.commit()
            return updated

    updated = run_async(_refresh())
    return {"updated": updated}
