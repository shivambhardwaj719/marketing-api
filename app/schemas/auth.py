from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import BaseSchema


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(min_length=8, max_length=64)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class FacebookCallbackRequest(BaseSchema):
    code: str
    state: str | None = None


class UserResponse(BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str | None
    profile_picture: str | None
    is_active: bool
    has_password: bool = False
    created_at: datetime


class FacebookOAuthURL(BaseSchema):
    oauth_url: str
    state: str
