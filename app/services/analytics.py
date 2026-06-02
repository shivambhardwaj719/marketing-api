from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.campaign import Campaign
from app.repositories.campaign import CampaignRepository
from app.repositories.lead import LeadRepository
from app.schemas.analytics import (
    CampaignPerformanceItem,
    DailyLeadStats,
    DashboardResponse,
    DateRangeFilter,
    LeadCountResponse,
)

logger = get_logger(__name__)


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lead_repo = LeadRepository(session)
        self.campaign_repo = CampaignRepository(session)

    async def get_dashboard(self, user_id: uuid.UUID) -> DashboardResponse:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        # Lead counts
        total_leads = await self.lead_repo.count([self.lead_repo.model.user_id == user_id])
        leads_today = await self.lead_repo.count_by_date_range(user_id, today_start, now)
        leads_week = await self.lead_repo.count_by_date_range(user_id, week_start, now)
        leads_month = await self.lead_repo.count_by_date_range(user_id, month_start, now)

        # Status breakdown
        status_counts = await self.lead_repo.count_by_status(user_id)
        lead_status = LeadCountResponse(
            total=total_leads,
            new=status_counts.get("new", 0),
            contacted=status_counts.get("contacted", 0),
            qualified=status_counts.get("qualified", 0),
            converted=status_counts.get("converted", 0),
            lost=status_counts.get("lost", 0),
        )

        # Campaign stats
        total_campaigns = await self.campaign_repo.count_by_user(user_id)
        active_campaigns = await self.campaign_repo.count_active_by_user(user_id)

        # Pages & ad accounts counts
        from app.models.facebook_page import FacebookPage
        from app.models.ad_account import AdAccount
        from sqlalchemy import func

        pages_result = await self.session.execute(
            select(func.count()).select_from(FacebookPage).where(
                FacebookPage.user_id == user_id, FacebookPage.is_active.is_(True)
            )
        )
        total_pages = pages_result.scalar_one()

        ad_accs_result = await self.session.execute(
            select(func.count()).select_from(AdAccount).where(
                AdAccount.user_id == user_id, AdAccount.is_active.is_(True)
            )
        )
        total_ad_accounts = ad_accs_result.scalar_one()

        # Top campaigns
        top_camp_rows = await self.lead_repo.top_campaigns_by_leads(user_id, limit=5)
        top_campaigns: list[CampaignPerformanceItem] = []
        for camp_id, lead_count in top_camp_rows:
            camp = await self.campaign_repo.get(camp_id)
            if camp:
                top_campaigns.append(
                    CampaignPerformanceItem(
                        campaign_id=camp.campaign_id,
                        campaign_name=camp.name,
                        lead_count=lead_count,
                    )
                )

        # Daily leads (last 30 days)
        thirty_days_ago = now - timedelta(days=30)
        daily_rows = await self.lead_repo.daily_lead_counts(user_id, thirty_days_ago, now)
        daily_leads = [DailyLeadStats(date=row[0], count=row[1]) for row in daily_rows]

        return DashboardResponse(
            total_leads=total_leads,
            leads_today=leads_today,
            leads_this_week=leads_week,
            leads_this_month=leads_month,
            total_campaigns=total_campaigns,
            active_campaigns=active_campaigns,
            total_pages=total_pages,
            total_ad_accounts=total_ad_accounts,
            lead_status_breakdown=lead_status,
            top_campaigns=top_campaigns,
            daily_leads=daily_leads,
        )

    async def get_campaign_performance(
        self, user_id: uuid.UUID, filters: DateRangeFilter
    ) -> list[CampaignPerformanceItem]:
        from app.models.lead import Lead
        from sqlalchemy import func

        stmt = (
            select(Campaign, func.count(Lead.id).label("lead_count"))
            .outerjoin(Lead, Lead.campaign_id == Campaign.id)
            .where(Campaign.user_id == user_id)
            .group_by(Campaign.id)
            .order_by(func.count(Lead.id).desc())
        )
        if filters.campaign_id:
            stmt = stmt.where(Campaign.id == filters.campaign_id)
        if filters.ad_account_id:
            stmt = stmt.where(Campaign.ad_account_id == filters.ad_account_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            CampaignPerformanceItem(
                campaign_id=row[0].campaign_id,
                campaign_name=row[0].name,
                lead_count=row[1],
            )
            for row in rows
        ]

    async def get_leads_count(
        self, user_id: uuid.UUID, filters: DateRangeFilter
    ) -> LeadCountResponse:
        from app.models.lead import Lead
        from sqlalchemy import and_

        base_filters = [Lead.user_id == user_id]
        if filters.date_from:
            base_filters.append(Lead.created_at >= datetime.combine(filters.date_from, datetime.min.time()))
        if filters.date_to:
            base_filters.append(Lead.created_at <= datetime.combine(filters.date_to, datetime.max.time()))
        if filters.campaign_id:
            base_filters.append(Lead.campaign_id == filters.campaign_id)

        from sqlalchemy import func, case
        result = await self.session.execute(
            select(
                func.count().label("total"),
                func.sum(case((Lead.status == "new", 1), else_=0)).label("new"),
                func.sum(case((Lead.status == "contacted", 1), else_=0)).label("contacted"),
                func.sum(case((Lead.status == "qualified", 1), else_=0)).label("qualified"),
                func.sum(case((Lead.status == "converted", 1), else_=0)).label("converted"),
                func.sum(case((Lead.status == "lost", 1), else_=0)).label("lost"),
            ).where(*base_filters)
        )
        row = result.one()
        return LeadCountResponse(
            total=row[0] or 0,
            new=row[1] or 0,
            contacted=row[2] or 0,
            qualified=row[3] or 0,
            converted=row[4] or 0,
            lost=row[5] or 0,
        )
