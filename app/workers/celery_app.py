from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "fastfacebook",
    broker=settings.REDIS_CELERY_BROKER,
    backend=settings.REDIS_CELERY_BACKEND,
    include=["app.workers.tasks.lead_tasks", "app.workers.tasks.campaign_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.lead_tasks.*": {"queue": "leads"},
        "app.workers.tasks.campaign_tasks.*": {"queue": "campaigns"},
    },
    beat_schedule={},
)
