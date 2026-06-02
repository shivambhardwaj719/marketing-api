from __future__ import annotations

import asyncio
import uuid

from celery import shared_task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def run_async(coro):
    """Run an async coroutine in Celery's sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.workers.tasks.lead_tasks.process_lead_from_webhook",
)
def process_lead_from_webhook(
    self,
    *,
    page_fb_id: str,
    lead_id: str,
    form_id: str,
    ad_id: str | None = None,
    adset_id: str | None = None,
    campaign_id: str | None = None,
    webhook_log_id: str | None = None,
) -> dict:
    """Celery task: fetch and store a lead from a Facebook webhook event."""

    async def _process():
        from app.core.database import AsyncSessionFactory
        from app.models.facebook_page import FacebookPage
        from app.models.user import User
        from app.services.lead import LeadService
        from sqlalchemy import select

        async with AsyncSessionFactory() as session:
            # Find the user who owns this page
            result = await session.execute(
                select(FacebookPage).where(FacebookPage.page_id == page_fb_id)
            )
            page = result.scalar_one_or_none()
            if not page:
                logger.warning("page_not_found_for_webhook", page_fb_id=page_fb_id)
                return {"status": "skipped", "reason": "page_not_found"}

            lead_service = LeadService(session)
            lead = await lead_service.process_webhook_lead(
                user_id=page.user_id,
                page_fb_id=page_fb_id,
                lead_id=lead_id,
                form_fb_id=form_id,
                ad_id=ad_id,
                adset_id=adset_id,
                campaign_id=campaign_id,
            )

            if webhook_log_id:
                from app.models.webhook_log import WebhookLog
                log = await session.get(WebhookLog, uuid.UUID(webhook_log_id))
                if log:
                    log.processing_status = "completed"
                    log.user_id = page.user_id

            await session.commit()
            return {"status": "ok", "lead_id": str(lead.id)}

    try:
        result = run_async(_process())
        logger.info("lead_processed", lead_id=lead_id, result=result)
        return result
    except Exception as exc:
        logger.exception("lead_task_failed", lead_id=lead_id, error=str(exc))
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _mark_webhook_log_failed(webhook_log_id, str(exc))
            return {"status": "failed", "error": str(exc)}


def _mark_webhook_log_failed(webhook_log_id: str | None, error: str) -> None:
    if not webhook_log_id:
        return

    async def _update():
        from app.core.database import AsyncSessionFactory
        from app.models.webhook_log import WebhookLog

        async with AsyncSessionFactory() as session:
            log = await session.get(WebhookLog, uuid.UUID(webhook_log_id))
            if log:
                log.processing_status = "failed"
                log.error_message = error
                log.retry_count += 1
                await session.commit()

    run_async(_update())


@celery_app.task(name="app.workers.tasks.lead_tasks.bulk_import_form_leads")
def bulk_import_form_leads(user_id: str, form_fb_id: str, page_fb_id: str) -> dict:
    """Celery task: bulk import all leads from a form."""

    async def _import():
        from app.core.database import AsyncSessionFactory
        from app.services.lead import LeadService

        async with AsyncSessionFactory() as session:
            service = LeadService(session)
            count = await service.fetch_form_leads(
                uuid.UUID(user_id), form_fb_id, page_fb_id
            )
            await session.commit()
            return count

    count = run_async(_import())
    return {"imported": count}
