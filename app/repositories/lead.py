from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Lead, session)

    async def get_by_facebook_lead_id(self, facebook_lead_id: str) -> Lead | None:
        result = await self.session.execute(
            select(Lead).where(Lead.facebook_lead_id == facebook_lead_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        campaign_id: uuid.UUID | None = None,
        adset_id: uuid.UUID | None = None,
        form_id: uuid.UUID | None = None,
        page_id: uuid.UUID | None = None,
        facebook_page_id: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
    ) -> tuple[list[Lead], int]:
        filters = [Lead.user_id == user_id]
        if campaign_id:
            filters.append(Lead.campaign_id == campaign_id)
        if adset_id:
            filters.append(Lead.adset_id == adset_id)
        if form_id:
            filters.append(Lead.form_id == form_id)
        if page_id:
            filters.append(Lead.page_id == page_id)
        if facebook_page_id:
            filters.append(Lead.facebook_page_id == facebook_page_id)
        if status:
            filters.append(Lead.status == status)
        if date_from:
            filters.append(Lead.created_at >= date_from)
        if date_to:
            filters.append(Lead.created_at <= date_to)
        if search:
            from sqlalchemy import or_
            filters.append(
                or_(
                    Lead.email.ilike(f"%{search}%"),
                    Lead.full_name.ilike(f"%{search}%"),
                    Lead.phone.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(Lead).where(*filters)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Lead)
            .where(*filters)
            .order_by(Lead.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def count_by_status(self, user_id: uuid.UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.user_id == user_id)
            .group_by(Lead.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def count_by_date_range(
        self,
        user_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.user_id == user_id,
                Lead.created_at >= date_from,
                Lead.created_at <= date_to,
            )
        )
        return result.scalar_one()

    async def daily_lead_counts(
        self, user_id: uuid.UUID, date_from: datetime, date_to: datetime
    ) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(
                func.date(Lead.created_at).label("date"),
                func.count(Lead.id).label("count"),
            )
            .where(
                Lead.user_id == user_id,
                Lead.created_at >= date_from,
                Lead.created_at <= date_to,
            )
            .group_by(func.date(Lead.created_at))
            .order_by(func.date(Lead.created_at))
        )
        return [(str(row[0]), row[1]) for row in result.all()]

    async def top_campaigns_by_leads(
        self, user_id: uuid.UUID, limit: int = 5
    ) -> list[tuple[uuid.UUID, int]]:
        result = await self.session.execute(
            select(Lead.campaign_id, func.count(Lead.id).label("lead_count"))
            .where(Lead.user_id == user_id, Lead.campaign_id.isnot(None))
            .group_by(Lead.campaign_id)
            .order_by(func.count(Lead.id).desc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in result.all()]
