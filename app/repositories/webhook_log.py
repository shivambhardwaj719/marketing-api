from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_log import WebhookLog
from app.repositories.base import BaseRepository


class WebhookLogRepository(BaseRepository[WebhookLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(WebhookLog, session)
