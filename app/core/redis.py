from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def publish_new_lead(user_id: str, lead_data: dict[str, Any]) -> None:
    """Publish a new lead event to the user's Redis channel."""
    try:
        r = await get_redis()
        channel = f"leads:{user_id}"
        await r.publish(channel, json.dumps(lead_data, default=str))
        logger.info("lead_published_to_redis", user_id=user_id, channel=channel)
    except Exception as exc:
        logger.warning("redis_publish_failed", user_id=user_id, error=str(exc))
