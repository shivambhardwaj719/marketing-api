from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import get_logger
from app.core.security import decrypt_token
from app.integrations.facebook.client import FacebookGraphClient
from app.models.lead import Lead
from app.repositories.lead import LeadRepository
from app.schemas.lead import LeadFilterParams

logger = get_logger(__name__)


def _extract_field(field_data: list[dict], name: str) -> str | None:
    for f in field_data:
        if f.get("name") == name:
            values = f.get("values", [])
            return values[0] if values else None
    return None


class LeadService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lead_repo = LeadRepository(session)

    async def _save_lead_from_data(
        self,
        user_id: uuid.UUID,
        page_fb_id: str,
        form_fb_id: str,
        lead_data: dict[str, Any],
        *,
        page_db_id: uuid.UUID | None = None,
        ig_account_db_id: uuid.UUID | None = None,
    ) -> Lead:
        """
        Save a lead directly from pre-fetched Graph API data.
        No extra API calls — used by all bulk fetch methods.
        page_db_id and ig_account_db_id can be passed as a cache to avoid
        repeated DB lookups when saving many leads for the same page.
        """
        lead_id = lead_data["id"]
        field_data: list[dict] = lead_data.get("field_data", [])

        email = _extract_field(field_data, "email")
        phone = _extract_field(field_data, "phone_number") or _extract_field(field_data, "phone")
        first_name = _extract_field(field_data, "first_name") or ""
        last_name = _extract_field(field_data, "last_name") or ""
        full_name = (
            _extract_field(field_data, "full_name")
            or f"{first_name} {last_name}".strip()
            or None
        )

        ad_id = lead_data.get("ad_id")
        adset_id = lead_data.get("adset_id")
        campaign_id = lead_data.get("campaign_id")
        platform = lead_data.get("platform")

        # Resolve optional DB foreign keys
        campaign_db_id = None
        adset_db_id = None
        ad_db_id = None
        form_db_id = None

        if campaign_id:
            from app.models.campaign import Campaign
            res = await self.session.execute(
                select(Campaign).where(Campaign.campaign_id == campaign_id)
            )
            c = res.scalar_one_or_none()
            if c:
                campaign_db_id = c.id

        if adset_id:
            from app.models.adset import Adset
            res = await self.session.execute(
                select(Adset).where(Adset.adset_id == adset_id)
            )
            a = res.scalar_one_or_none()
            if a:
                adset_db_id = a.id

        if ad_id:
            from app.models.ad import Ad
            res = await self.session.execute(
                select(Ad).where(Ad.ad_id == ad_id)
            )
            ad_obj = res.scalar_one_or_none()
            if ad_obj:
                ad_db_id = ad_obj.id

        if form_fb_id:
            from app.models.form import LeadForm
            res = await self.session.execute(
                select(LeadForm).where(LeadForm.form_id == form_fb_id)
            )
            f = res.scalar_one_or_none()
            if f:
                form_db_id = f.id

        lead = Lead(
            user_id=user_id,
            campaign_id=campaign_db_id,
            adset_id=adset_db_id,
            ad_id=ad_db_id,
            form_id=form_db_id,
            page_id=page_db_id,
            instagram_account_id=ig_account_db_id,
            facebook_lead_id=lead_id,
            facebook_campaign_id=campaign_id,
            facebook_adset_id=adset_id,
            facebook_ad_id=ad_id,
            facebook_form_id=form_fb_id,
            facebook_page_id=page_fb_id,
            field_data=field_data,
            email=email,
            phone=phone,
            full_name=full_name,
            platform=platform,
            placement=lead_data.get("placement"),
            is_organic=lead_data.get("is_organic"),
            status="new",
        )
        await self.lead_repo.create(lead)
        logger.info("lead_created", lead_id=lead_id, email=email)

        try:
            from app.core.redis import publish_new_lead
            await publish_new_lead(str(user_id), {
                "id": str(lead.id),
                "facebook_lead_id": lead_id,
                "email": email,
                "full_name": full_name,
                "phone": phone,
                "status": "new",
                "platform": lead_data.get("platform"),
                "facebook_page_id": page_fb_id,
                "facebook_form_id": form_fb_id,
                "facebook_campaign_id": campaign_id,
                "facebook_adset_id": adset_id,
                "facebook_ad_id": ad_id,
                "field_data": field_data,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            })
        except Exception:
            pass

        return lead

    async def process_webhook_lead(
        self,
        user_id: uuid.UUID,
        page_fb_id: str,
        lead_id: str,
        form_fb_id: str,
        ad_id: str | None = None,
        adset_id: str | None = None,
        campaign_id: str | None = None,
    ) -> Lead:
        """Used by real-time webhook events — fetches full lead data by ID then saves."""
        existing = await self.lead_repo.get_by_facebook_lead_id(lead_id)
        if existing:
            logger.info("lead_already_exists", lead_id=lead_id)
            return existing

        from app.models.facebook_account import FacebookAccount
        from app.models.facebook_page import FacebookPage

        fb_page_result = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.page_id == page_fb_id,
                FacebookPage.user_id == user_id,
            )
        )
        fb_page = fb_page_result.scalar_one_or_none()

        fb_accts = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.user_id == user_id)
        )
        fb_account = fb_accts.scalars().first()
        if not fb_account:
            raise NotFoundError("No Facebook account for user")

        token = decrypt_token(fb_account.access_token_encrypted)

        async with FacebookGraphClient(token) as client:
            lead_data = await client.get_lead(lead_id)

        # Merge ad/adset/campaign IDs from webhook payload if not in lead_data
        if ad_id and not lead_data.get("ad_id"):
            lead_data["ad_id"] = ad_id
        if adset_id and not lead_data.get("adset_id"):
            lead_data["adset_id"] = adset_id
        if campaign_id and not lead_data.get("campaign_id"):
            lead_data["campaign_id"] = campaign_id

        page_db_id = fb_page.id if fb_page else None
        ig_account_db_id = None
        if lead_data.get("platform") == "ig" and fb_page:
            from app.models.instagram_account import InstagramAccount
            res = await self.session.execute(
                select(InstagramAccount).where(
                    InstagramAccount.facebook_page_id == fb_page.id
                )
            )
            ig = res.scalar_one_or_none()
            if ig:
                ig_account_db_id = ig.id

        return await self._save_lead_from_data(
            user_id, page_fb_id, form_fb_id, lead_data,
            page_db_id=page_db_id,
            ig_account_db_id=ig_account_db_id,
        )

    async def list_leads(
        self,
        user_id: uuid.UUID,
        params: LeadFilterParams,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Lead], int]:
        offset = (page - 1) * page_size
        return await self.lead_repo.get_by_user(
            user_id,
            offset=offset,
            limit=page_size,
            campaign_id=params.campaign_id,
            adset_id=params.adset_id,
            form_id=params.form_id,
            page_id=params.page_id,
            status=params.status,
            date_from=params.date_from,
            date_to=params.date_to,
            search=params.search,
        )

    async def list_leads_by_facebook_page(
        self,
        user_id: uuid.UUID,
        facebook_page_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Lead], int]:
        offset = (page - 1) * page_size
        return await self.lead_repo.get_by_user(
            user_id,
            offset=offset,
            limit=page_size,
            facebook_page_id=facebook_page_id,
            status=status,
            search=search,
        )

    async def sync_page_leads(
        self,
        user_id: uuid.UUID,
        facebook_page_id: str,
    ) -> dict[str, Any]:
        """Pull all leads from every lead form on a Facebook Page into the DB."""
        token = await self._get_page_token_or_user_token(user_id, facebook_page_id)
        page_db_id, ig_account_db_id = await self._resolve_page_context(user_id, facebook_page_id)

        async with FacebookGraphClient(token) as client:
            forms = await client.get_lead_forms(facebook_page_id)

        if not forms:
            return {"page_id": facebook_page_id, "forms_found": 0, "leads_imported": 0, "leads_skipped": 0, "forms": []}

        total_imported = 0
        total_skipped = 0
        form_results = []

        for form in forms:
            form_id = form["id"]
            imported = 0
            skipped = 0
            after: str | None = None

            while True:
                async with FacebookGraphClient(token) as client:
                    data = await client.get_form_leads(form_id, after=after)

                for lead_raw in data.get("data", []):
                    if await self.lead_repo.get_by_facebook_lead_id(lead_raw["id"]):
                        skipped += 1
                    else:
                        try:
                            await self._save_lead_from_data(
                                user_id, facebook_page_id, form_id, lead_raw,
                                page_db_id=page_db_id,
                                ig_account_db_id=ig_account_db_id,
                            )
                            imported += 1
                        except Exception as exc:
                            logger.warning("lead_import_failed", lead_id=lead_raw["id"], error=str(exc))
                            skipped += 1

                paging = data.get("paging", {})
                after = paging.get("cursors", {}).get("after")
                if not after or not data.get("data"):
                    break

            total_imported += imported
            total_skipped += skipped
            form_results.append({
                "form_id": form_id,
                "form_name": form.get("name", ""),
                "imported": imported,
                "skipped": skipped,
            })

        return {
            "page_id": facebook_page_id,
            "forms_found": len(forms),
            "leads_imported": total_imported,
            "leads_skipped": total_skipped,
            "forms": form_results,
        }

    async def get_lead(self, user_id: uuid.UUID, lead_db_id: uuid.UUID) -> Lead:
        lead = await self.lead_repo.get(lead_db_id)
        if not lead or lead.user_id != user_id:
            raise NotFoundError("Lead not found")
        return lead

    async def update_lead_status(
        self, user_id: uuid.UUID, lead_db_id: uuid.UUID, status: str
    ) -> Lead:
        lead = await self.get_lead(user_id, lead_db_id)
        await self.lead_repo.update(lead, {"status": status})
        return lead

    async def _get_page_token_or_user_token(self, user_id: uuid.UUID, page_fb_id: str) -> str:
        """
        Returns a Page Access Token for page_fb_id.
        Always attempts a fresh fetch from /me/accounts (which returns proper
        per-page tokens) and persists the result. Falls back to the stored page
        token, then the user token.
        """
        from app.models.facebook_page import FacebookPage
        from app.models.facebook_account import FacebookAccount
        from app.core.security import encrypt_token as _enc

        fb_accts = await self.session.execute(
            select(FacebookAccount).where(FacebookAccount.user_id == user_id)
        )
        fb_account = fb_accts.scalars().first()
        if not fb_account:
            raise NotFoundError("No Facebook account connected")

        user_token = decrypt_token(
            fb_account.long_lived_token_encrypted or fb_account.access_token_encrypted
        )

        # /me/accounts returns a proper Page Access Token for each page the user manages
        try:
            async with FacebookGraphClient(user_token) as client:
                accounts_data = await client.get("/me/accounts", fields="id,access_token")
            for acc in accounts_data.get("data", []):
                if acc.get("id") == page_fb_id and acc.get("access_token"):
                    page_token = acc["access_token"]
                    # Persist so the next call doesn't need to refetch
                    res = await self.session.execute(
                        select(FacebookPage).where(
                            FacebookPage.page_id == page_fb_id,
                            FacebookPage.user_id == user_id,
                        )
                    )
                    fb_page = res.scalar_one_or_none()
                    if fb_page:
                        fb_page.page_access_token_encrypted = _enc(page_token)
                        await self.session.flush()
                    logger.info("page_token_refreshed", page_id=page_fb_id)
                    return page_token
        except Exception as exc:
            logger.warning("page_token_refresh_failed", page_id=page_fb_id, error=str(exc))

        # Fall back to whatever is stored in DB for this page
        res = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.page_id == page_fb_id,
                FacebookPage.user_id == user_id,
            )
        )
        fb_page = res.scalar_one_or_none()
        if fb_page and fb_page.page_access_token_encrypted:
            return decrypt_token(fb_page.page_access_token_encrypted)

        return user_token

    async def _resolve_page_context(
        self, user_id: uuid.UUID, page_fb_id: str
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        """Returns (page_db_id, ig_account_db_id) for a given FB page — cached once per call."""
        from app.models.facebook_page import FacebookPage
        from app.models.instagram_account import InstagramAccount

        res = await self.session.execute(
            select(FacebookPage).where(
                FacebookPage.page_id == page_fb_id,
                FacebookPage.user_id == user_id,
            )
        )
        fb_page = res.scalar_one_or_none()
        page_db_id = fb_page.id if fb_page else None
        ig_account_db_id = None
        if fb_page:
            res2 = await self.session.execute(
                select(InstagramAccount).where(
                    InstagramAccount.facebook_page_id == fb_page.id
                )
            )
            ig = res2.scalar_one_or_none()
            if ig:
                ig_account_db_id = ig.id
        return page_db_id, ig_account_db_id

    async def fetch_form_leads(
        self, user_id: uuid.UUID, form_fb_id: str, page_fb_id: str
    ) -> int:
        token = await self._get_page_token_or_user_token(user_id, page_fb_id)
        # Resolve page context once — reused for every lead in this form
        page_db_id, ig_account_db_id = await self._resolve_page_context(user_id, page_fb_id)
        count = 0
        after: str | None = None

        while True:
            async with FacebookGraphClient(token) as client:
                data = await client.get_form_leads(form_fb_id, after=after)

            for lead_raw in data.get("data", []):
                if await self.lead_repo.get_by_facebook_lead_id(lead_raw["id"]):
                    continue
                await self._save_lead_from_data(
                    user_id, page_fb_id, form_fb_id, lead_raw,
                    page_db_id=page_db_id,
                    ig_account_db_id=ig_account_db_id,
                )
                count += 1

            paging = data.get("paging", {})
            after = paging.get("cursors", {}).get("after")
            if not after or not data.get("data"):
                break

        return count

    async def fetch_page_leads(
        self, user_id: uuid.UUID, page_fb_id: str
    ) -> dict[str, Any]:
        token = await self._get_page_token_or_user_token(user_id, page_fb_id)
        page_db_id, ig_account_db_id = await self._resolve_page_context(user_id, page_fb_id)
        total_imported = 0
        total_skipped = 0

        async with FacebookGraphClient(token) as client:
            forms = await client.get_lead_forms(page_fb_id)

        if not forms:
            return {"page_id": page_fb_id, "forms_found": 0, "imported": 0, "skipped": 0, "total": 0}

        for form in forms:
            form_fb_id = form["id"]
            after: str | None = None

            while True:
                async with FacebookGraphClient(token) as client:
                    data = await client.get_form_leads(form_fb_id, after=after)

                for lead_raw in data.get("data", []):
                    if await self.lead_repo.get_by_facebook_lead_id(lead_raw["id"]):
                        total_skipped += 1
                    else:
                        try:
                            await self._save_lead_from_data(
                                user_id, page_fb_id, form_fb_id, lead_raw,
                                page_db_id=page_db_id,
                                ig_account_db_id=ig_account_db_id,
                            )
                            total_imported += 1
                        except Exception as exc:
                            logger.warning("lead_import_failed", lead_id=lead_raw["id"], error=str(exc))
                            total_skipped += 1

                paging = data.get("paging", {})
                after = paging.get("cursors", {}).get("after")
                if not after or not data.get("data"):
                    break

        return {
            "page_id": page_fb_id,
            "forms_found": len(forms),
            "imported": total_imported,
            "skipped": total_skipped,
            "total": total_imported + total_skipped,
        }

    async def fetch_leads_by_asset(
        self,
        user_id: uuid.UUID,
        asset_id: str,
        business_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch all leads tied to a given asset (page ID) and optionally a
        Business Manager. Lead forms are collected from both the asset and
        the business (when provided), deduplicated, then all leads are
        pulled and stored.
        """
        token = await self._get_page_token_or_user_token(user_id, asset_id)

        forms_map: dict[str, dict] = {}

        async with FacebookGraphClient(token) as client:
            # Treat asset_id as a Facebook Page ID
            try:
                asset_forms = await client.get_lead_forms(asset_id)
                for f in asset_forms:
                    forms_map[f["id"]] = {"form": f, "page_id": asset_id}
            except Exception as exc:
                logger.warning("fetch_asset_forms_failed", asset_id=asset_id, error=str(exc))

            # Also pull from business if provided
            if business_id:
                try:
                    biz_forms = await client.get_business_lead_forms(business_id)
                    for f in biz_forms:
                        if f["id"] not in forms_map:
                            page_info = f.get("page", {})
                            forms_map[f["id"]] = {
                                "form": f,
                                "page_id": page_info.get("id", asset_id),
                            }
                except Exception as exc:
                    logger.warning("fetch_business_forms_failed", business_id=business_id, error=str(exc))

        if not forms_map:
            return {"forms_found": 0, "leads_imported": 0, "leads_skipped": 0}

        # Resolve page context once per unique page_id in the form map
        page_context_cache: dict[str, tuple[uuid.UUID | None, uuid.UUID | None]] = {}

        total_imported = 0
        total_skipped = 0
        form_results = []

        for form_id, meta in forms_map.items():
            page_id = meta["page_id"]
            if page_id not in page_context_cache:
                page_context_cache[page_id] = await self._resolve_page_context(user_id, page_id)
            page_db_id, ig_account_db_id = page_context_cache[page_id]

            imported = 0
            skipped = 0
            after: str | None = None

            while True:
                async with FacebookGraphClient(token) as client:
                    data = await client.get_form_leads(form_id, after=after)

                for lead_raw in data.get("data", []):
                    if await self.lead_repo.get_by_facebook_lead_id(lead_raw["id"]):
                        skipped += 1
                    else:
                        try:
                            await self._save_lead_from_data(
                                user_id, page_id, form_id, lead_raw,
                                page_db_id=page_db_id,
                                ig_account_db_id=ig_account_db_id,
                            )
                            imported += 1
                        except Exception as exc:
                            logger.warning("lead_import_failed", lead_id=lead_raw["id"], error=str(exc))
                            skipped += 1

                paging = data.get("paging", {})
                after = paging.get("cursors", {}).get("after")
                if not after or not data.get("data"):
                    break

            total_imported += imported
            total_skipped += skipped
            form_results.append({
                "form_id": form_id,
                "form_name": meta["form"].get("name", ""),
                "page_id": page_id,
                "imported": imported,
                "skipped": skipped,
            })

        return {
            "asset_id": asset_id,
            "business_id": business_id,
            "forms_found": len(forms_map),
            "leads_imported": total_imported,
            "leads_skipped": total_skipped,
            "forms": form_results,
        }

