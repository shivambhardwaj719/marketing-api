from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, FacebookAuthError
from app.core.logger import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_token,
    decode_token,
    encrypt_token,
    hash_password,
    verify_password,
)
from app.integrations.facebook.client import FacebookGraphClient
from app.models.facebook_account import FacebookAccount
from app.models.user import User
from app.repositories.facebook_account import FacebookAccountRepository
from app.repositories.user import UserRepository
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.fb_account_repo = FacebookAccountRepository(session)

    def get_oauth_url(self) -> dict[str, str]:
        from app.core.config import settings

        state = secrets.token_urlsafe(16)
        return {"oauth_url": settings.facebook_oauth_url + f"&state={state}", "state": state}

    async def facebook_callback(self, code: str) -> TokenResponse:
        token_data = await FacebookGraphClient.exchange_code_for_token(code)
        short_token = token_data.get("access_token", "")
        if not short_token:
            raise FacebookAuthError("No access token returned from Facebook")

        extended = await FacebookGraphClient.extend_token(short_token)
        long_token = extended.get("access_token", short_token)

        async with FacebookGraphClient(long_token) as client:
            fb_user = await client.get_me()

        fb_user_id = fb_user["id"]
        email = fb_user.get("email", f"{fb_user_id}@facebook.com")
        name = fb_user.get("name")
        picture = fb_user.get("picture", {}).get("data", {}).get("url")

        user = await self.user_repo.get_by_email(email)
        if not user:
            user = User(
                email=email,
                full_name=name,
                profile_picture=picture,
                is_active=True,
            )
            await self.user_repo.create(user)
        else:
            await self.user_repo.update(
                user, {"full_name": name, "profile_picture": picture}
            )

        fb_account = await self.fb_account_repo.get_by_facebook_id(fb_user_id)
        encrypted_token = encrypt_token(long_token)
        expires_at = extended.get("expires_in")

        if not fb_account:
            fb_account = FacebookAccount(
                user_id=user.id,
                facebook_user_id=fb_user_id,
                name=name,
                email=email,
                profile_picture=picture,
                access_token_encrypted=encrypted_token,
                long_lived_token_encrypted=encrypted_token,
                token_expires_at=str(expires_at) if expires_at else None,
                is_active=True,
            )
            await self.fb_account_repo.create(fb_account)
        else:
            await self.fb_account_repo.update(
                fb_account,
                {
                    "user_id": user.id,
                    "name": name,
                    "email": email,
                    "profile_picture": picture,
                    "access_token_encrypted": encrypted_token,
                    "long_lived_token_encrypted": encrypted_token,
                    "token_expires_at": str(expires_at) if expires_at else None,
                    "is_active": True,
                },
            )

        from app.core.config import settings

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        from app.core.config import settings

        payload = decode_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid refresh token")

        user = await self.user_repo.get_active(user_id)
        if not user:
            raise AuthenticationError("User not found or inactive")

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def register(self, data: RegisterRequest) -> TokenResponse:
        from app.core.config import settings

        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError("An account with this email already exists")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            is_active=True,
        )
        await self.user_repo.create(user)
        logger.info("user_registered", email=user.email, user_id=str(user.id))

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        from app.core.config import settings

        user = await self.user_repo.get_by_email(data.email)
        if not user or not user.hashed_password:
            raise AuthenticationError("Invalid email or password")
        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        logger.info("user_login", email=user.email, user_id=str(user.id))
        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not user.hashed_password:
            raise AuthenticationError("No password set — use Facebook login")
        if not verify_password(data.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")
        await self.user_repo.update(
            user, {"hashed_password": hash_password(data.new_password)}
        )
        logger.info("password_changed", user_id=str(user.id))

    async def get_current_user(self, token: str) -> User:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        user = await self.user_repo.get_active(user_id)
        if not user:
            raise AuthenticationError("User not found or inactive")
        return user
