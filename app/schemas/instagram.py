from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class InstagramAccountResponse(UUIDSchema, TimestampSchema):
    facebook_page_id: uuid.UUID
    instagram_account_id: str
    username: str
    profile_picture: str | None


