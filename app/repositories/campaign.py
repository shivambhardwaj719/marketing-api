from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Campaign, session)

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[Campaign]:
        stmt = select(Campaign).where(Campaign.user_id == user_id)
        if status:
            stmt = stmt.where(Campaign.status == status)
        stmt = stmt.order_by(Campaign.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_campaign_id(self, campaign_fb_id: str) -> Campaign | None:
        result = await self.session.execute(
            select(Campaign).where(Campaign.campaign_id == campaign_fb_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> Campaign | None:
        result = await self.session.execute(
            select(Campaign).where(
                Campaign.user_id == user_id, Campaign.id == campaign_id
            )
        )
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Campaign).where(Campaign.user_id == user_id)
        )
        return result.scalar_one()

    async def count_active_by_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Campaign)
            .where(Campaign.user_id == user_id, Campaign.status == "ACTIVE")
        )
        return result.scalar_one()
