from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.facebook_account import FacebookAccount
from app.repositories.base import BaseRepository


class FacebookAccountRepository(BaseRepository[FacebookAccount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FacebookAccount, session)

    async def get_by_user(self, user_id: uuid.UUID) -> list[FacebookAccount]:
        result = await self.session.execute(
            select(FacebookAccount)
            .where(FacebookAccount.user_id == user_id, FacebookAccount.is_active.is_(True))
            .options(
                selectinload(FacebookAccount.pages),
                selectinload(FacebookAccount.ad_accounts),
            )
        )
        return list(result.scalars().all())

    async def get_by_facebook_id(self, facebook_user_id: str) -> FacebookAccount | None:
        result = await self.session.execute(
            select(FacebookAccount).where(
                FacebookAccount.facebook_user_id == facebook_user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> FacebookAccount | None:
        result = await self.session.execute(
            select(FacebookAccount).where(
                FacebookAccount.user_id == user_id,
                FacebookAccount.id == account_id,
                FacebookAccount.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
