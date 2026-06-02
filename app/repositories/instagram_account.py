import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instagram_account import InstagramAccount


class InstagramAccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: uuid.UUID) -> Sequence[InstagramAccount]:
        result = await self.session.execute(
            select(InstagramAccount)
            .where(InstagramAccount.user_id == user_id)
            .options(selectinload(InstagramAccount.facebook_page))
        )
        return result.scalars().all()

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, instagram_account_db_id: uuid.UUID
    ) -> InstagramAccount | None:
        result = await self.session.execute(
            select(InstagramAccount)
            .where(
                InstagramAccount.user_id == user_id,
                InstagramAccount.id == instagram_account_db_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_instagram_account_id(
        self, instagram_account_id: str
    ) -> InstagramAccount | None:
        result = await self.session.execute(
            select(InstagramAccount)
            .where(InstagramAccount.instagram_account_id == instagram_account_id)
        )
        return result.scalar_one_or_none()
