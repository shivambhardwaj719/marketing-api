from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.logger import get_logger
from app.core.security import decrypt_token, encrypt_token
from app.integrations.facebook.client import FacebookGraphClient
from app.models.ad_account import AdAccount
from app.models.facebook_account import FacebookAccount
from app.models.facebook_page import FacebookPage
from app.repositories.facebook_account import FacebookAccountRepository
from app.schemas.facebook import (
    AdAccountResponse,
    FacebookAccountResponse,
    FacebookPageResponse,
)

logger = get_logger(__name__)


class FacebookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.fb_account_repo = FacebookAccountRepository(session)

    async def _get_fb_account_token(
        self, user_id: uuid.UUID, fb_account_id: uuid.UUID
    ) -> tuple[FacebookAccount, str]:
        account = await self.fb_account_repo.get_by_user_and_id(user_id, fb_account_id)
        if not account:
            raise NotFoundError("Facebook account not found")
        token = decrypt_token(account.long_lived_token_encrypted or account.access_token_encrypted)
        return account, token

    async def get_connected_accounts(self, user_id: uuid.UUID) -> list[FacebookAccount]:
        return await self.fb_account_repo.get_by_user(user_id)

    async def get_all_user_pages(self, user_id: uuid.UUID) -> list[FacebookPage]:
        """Return all Facebook Pages stored in DB for the user, across all connected accounts."""
        from sqlalchemy import select
        from app.models.facebook_page import FacebookPage as PageModel

        result = await self.session.execute(
            select(PageModel)
            .where(PageModel.user_id == user_id)
            .order_by(PageModel.name)
        )
        return list(result.scalars().all())

    async def sync_all_user_pages(self, user_id: uuid.UUID) -> list[FacebookPage]:
        """Sync pages from every connected Facebook account and return the full list."""
        accounts = await self.fb_account_repo.get_by_user(user_id)
        for account in accounts:
            await self.sync_pages(user_id, account.id)
        return await self.get_all_user_pages(user_id)

    async def get_pages(self, user_id: uuid.UUID, fb_account_id: uuid.UUID) -> list[FacebookPage]:
        from sqlalchemy import select
        from app.models.facebook_page import FacebookPage as PageModel
        
        result = await self.session.execute(
            select(PageModel).where(
                PageModel.facebook_account_id == fb_account_id,
                PageModel.user_id == user_id
            )
        )
        return list(result.scalars().all())

    async def sync_pages(self, user_id: uuid.UUID, fb_account_id: uuid.UUID) -> list[FacebookPage]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)

        async with FacebookGraphClient(token) as client:
            pages_data = await client.get_pages()

        from sqlalchemy import select
        from app.models.facebook_page import FacebookPage as PageModel

        synced: list[FacebookPage] = []
        for page_data in pages_data:
            result = await self.session.execute(
                select(PageModel).where(PageModel.page_id == page_data["id"])
            )
            existing = result.scalar_one_or_none()
            page_token = page_data.get("access_token", "")
            if not existing:
                page = PageModel(
                    facebook_account_id=account.id,
                    user_id=user_id,
                    page_id=page_data["id"],
                    name=page_data.get("name", ""),
                    category=page_data.get("category"),
                    picture_url=page_data.get("picture", {}).get("data", {}).get("url"),
                    page_access_token_encrypted=(
                        encrypt_token(page_token) if page_token else None
                    ),
                    is_active=True,
                )
                self.session.add(page)
                synced.append(page)
            else:
                if page_token:
                    existing.page_access_token_encrypted = encrypt_token(page_token)
                existing.name = page_data.get("name", existing.name)
                synced.append(existing)

        await self.session.flush()
        return synced

    async def sync_ad_accounts(
        self, user_id: uuid.UUID, fb_account_id: uuid.UUID
    ) -> list[AdAccount]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)

        async with FacebookGraphClient(token) as client:
            accounts_data = await client.get_ad_accounts()
            
            # Also fetch from all businesses the user has access to
            businesses = await client.get_businesses()
            for b in businesses:
                b_accounts = await client.get_business_ad_accounts(b["id"])
                accounts_data.extend(b_accounts)

        # Deduplicate raw accounts data by id
        seen = set()
        unique_accounts = []
        for acc in accounts_data:
            if acc["id"] not in seen:
                unique_accounts.append(acc)
                seen.add(acc["id"])
        
        accounts_data = unique_accounts

        from sqlalchemy import select

        synced: list[AdAccount] = []
        for acc_data in accounts_data:
            raw_id = acc_data["id"].replace("act_", "")
            result = await self.session.execute(
                select(AdAccount).where(AdAccount.account_id == raw_id)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                ad_acc = AdAccount(
                    facebook_account_id=account.id,
                    user_id=user_id,
                    account_id=raw_id,
                    account_name=acc_data.get("name"),
                    currency=acc_data.get("currency"),
                    timezone=acc_data.get("timezone_name"),
                    account_status=acc_data.get("account_status"),
                    is_active=True,
                )
                self.session.add(ad_acc)
                synced.append(ad_acc)
            else:
                existing.account_name = acc_data.get("name", existing.account_name)
                existing.account_status = acc_data.get("account_status", existing.account_status)
                synced.append(existing)

        await self.session.flush()
        return synced

    async def subscribe_page_webhook(
        self, user_id: uuid.UUID, page_db_id: uuid.UUID
    ) -> dict[str, Any]:
        from sqlalchemy import select

        result = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.id == page_db_id, FacebookPage.user_id == user_id
            )
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError("Page not found")

        from app.core.security import decrypt_token as dec

        page_token = dec(page.page_access_token_encrypted) if page.page_access_token_encrypted else None
        if not page_token:
            raise PermissionDeniedError("Page access token not available")

        async with FacebookGraphClient(page_token) as client:
            resp = await client.subscribe_page_to_app(page.page_id, page_token)

        page.webhook_subscribed = resp.get("success", False)
        await self.session.flush()
        return resp

    async def get_lead_forms(
        self, user_id: uuid.UUID, page_db_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        result = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.id == page_db_id, FacebookPage.user_id == user_id
            )
        )
        page = result.scalar_one_or_none()
        if not page:
            raise NotFoundError("Page not found")

        fb_accounts = await self.fb_account_repo.get_by_user(user_id)
        if not fb_accounts:
            raise NotFoundError("No Facebook account connected")

        token = decrypt_token(fb_accounts[0].access_token_encrypted)
        async with FacebookGraphClient(token) as client:
            forms = await client.get_lead_forms(page.page_id)

        # Upsert forms into DB
        from app.models.form import LeadForm
        from app.core.security import encrypt_token

        for form_data in forms:
            res = await self.session.execute(
                select(LeadForm).where(LeadForm.form_id == form_data["id"])
            )
            existing_form = res.scalar_one_or_none()
            if not existing_form:
                lf = LeadForm(
                    page_id=page.id,
                    user_id=user_id,
                    form_id=form_data["id"],
                    name=form_data.get("name", ""),
                    status=form_data.get("status"),
                    questions=form_data.get("questions"),
                    locale=form_data.get("locale"),
                    follow_up_action_url=form_data.get("follow_up_action_url"),
                )
                self.session.add(lf)

        await self.session.flush()
        return forms

    # ─── Business Manager ───────────────────────────────────────────────────────

    async def get_businesses(self, user_id: uuid.UUID, fb_account_id: uuid.UUID) -> list[dict[str, Any]]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.get_businesses()

    async def get_business_ad_accounts(self, user_id: uuid.UUID, fb_account_id: uuid.UUID, business_id: str) -> list[dict[str, Any]]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.get_business_ad_accounts(business_id)

    # ─── Ad Creatives & Audiences ───────────────────────────────────────────────

    async def get_adcreatives(self, user_id: uuid.UUID, fb_account_id: uuid.UUID, ad_account_fb_id: str) -> list[dict[str, Any]]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.get_adcreatives(ad_account_fb_id)

    async def create_adcreative(self, user_id: uuid.UUID, fb_account_id: uuid.UUID, ad_account_fb_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.create_adcreative(ad_account_fb_id, payload)

    async def get_custom_audiences(self, user_id: uuid.UUID, fb_account_id: uuid.UUID, ad_account_fb_id: str) -> list[dict[str, Any]]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.get_custom_audiences(ad_account_fb_id)

    async def create_custom_audience(self, user_id: uuid.UUID, fb_account_id: uuid.UUID, ad_account_fb_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        account, token = await self._get_fb_account_token(user_id, fb_account_id)
        async with FacebookGraphClient(token) as client:
            return await client.create_custom_audience(ad_account_fb_id, payload)
