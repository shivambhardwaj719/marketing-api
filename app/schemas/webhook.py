from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WebhookVerificationParams(BaseModel):
    hub_mode: str | None = None
    hub_challenge: str | None = None
    hub_verify_token: str | None = None


class LeadgenChange(BaseModel):
    field: str
    value: dict[str, Any]


class WebhookEntry(BaseModel):
    id: str
    time: int
    changes: list[LeadgenChange] = []


class FacebookWebhookPayload(BaseModel):
    object: str
    entry: list[WebhookEntry]


class WebhookLogResponse(BaseModel):
    id: str
    event_type: str
    processing_status: str
    created_at: str
    error_message: str | None
    retry_count: int
