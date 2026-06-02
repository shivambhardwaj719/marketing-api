from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class FacebookPageResponse(UUIDSchema, TimestampSchema):
    page_id: str
    name: str
    category: str | None
    picture_url: str | None
    is_active: bool
    webhook_subscribed: bool


class AdAccountResponse(UUIDSchema, TimestampSchema):
    account_id: str
    account_name: str | None
    currency: str | None
    timezone: str | None
    account_status: int | None
    is_active: bool


class FacebookAccountResponse(UUIDSchema, TimestampSchema):
    facebook_user_id: str
    name: str | None
    email: str | None
    profile_picture: str | None
    is_active: bool
    pages: list[FacebookPageResponse] = []
    ad_accounts: list[AdAccountResponse] = []


class SyncPagesRequest(BaseSchema):
    facebook_account_id: uuid.UUID


class SubscribeWebhookRequest(BaseSchema):
    page_id: uuid.UUID
