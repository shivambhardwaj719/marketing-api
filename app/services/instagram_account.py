import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import FacebookAPIError, NotFoundError
from app.core.security import decrypt_token
from app.integrations.facebook.client import FacebookGraphClient
from app.models.facebook_page import FacebookPage
from app.models.instagram_account import InstagramAccount
from app.repositories.instagram_account import InstagramAccountRepository


class InstagramService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = InstagramAccountRepository(session)

    async def get_accounts(self, user_id: uuid.UUID) -> list[InstagramAccount]:
        return await self.repo.get_by_user(user_id)

    async def sync_accounts(self, user_id: uuid.UUID, page_db_id: uuid.UUID) -> InstagramAccount | None:
        """Fetch and sync the connected Instagram account for a given Facebook Page UUID."""
        from sqlalchemy import select

        page_result = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.user_id == user_id,
                FacebookPage.id == page_db_id,
            )
        )
        page = page_result.scalar_one_or_none()
        if not page:
            raise NotFoundError("Facebook Page not found")

        # Usually we use the user's access token or the page access token.
        # We will use the user's token here.
        from app.models.facebook_account import FacebookAccount
        fb_result = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.id == page.facebook_account_id)
        )
        fb_account = fb_result.scalar_one_or_none()
        if not fb_account:
            raise NotFoundError("Facebook Account not found")

        token = decrypt_token(fb_account.long_lived_token_encrypted or fb_account.access_token_encrypted)

        async with FacebookGraphClient(token) as client:
            ig_data = await client.get_instagram_business_account(page.page_id)

        if not ig_data:
            return None

        ig_account_id = ig_data.get("id")
        username = ig_data.get("username", "")
        profile_picture = ig_data.get("profile_picture_url")

        existing = await self.repo.get_by_instagram_account_id(ig_account_id)
        if existing:
            existing.username = username
            existing.profile_picture = profile_picture
            existing.facebook_page_id = page.id
            existing.access_token = fb_account.access_token_encrypted # Use FB access token
            await self.session.flush()
            return existing

        ig_account = InstagramAccount(
            user_id=user_id,
            facebook_page_id=page.id,
            instagram_account_id=ig_account_id,
            username=username,
            profile_picture=profile_picture,
            access_token=fb_account.access_token_encrypted
        )
        self.session.add(ig_account)
        await self.session.flush()
        return ig_account
