"""
Database seeder — seeds your real Facebook account data for testing.
Run: python scripts/seed.py
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.core.security import (
    create_access_token,
    create_refresh_token,
    encrypt_token,
    hash_password,
)
from app.models.ad_account import AdAccount
from app.models.facebook_account import FacebookAccount
from app.models.facebook_page import FacebookPage
from app.models.instagram_account import InstagramAccount
from app.models.user import User

# ── Real user data ─────────────────────────────────────────────────────────────

SEED_EMAIL = "shivam.b@telepathyinfotech.com"
SEED_PASSWORD = "Test@1234"
SEED_FULL_NAME = "Shivam B"
SEED_FB_USER_ID = "61570299452605"
SEED_FB_PAGE_ID = "ut7656765676"
SEED_AD_ACCOUNT_ID = "5979883519774883"
SEED_INSTAGRAM_ACCOUNT_ID = "17841472063796828"
SEED_PROFILE_PIC = f"https://graph.facebook.com/{SEED_FB_USER_ID}/picture?type=large"

PLACEHOLDER_TOKEN = "EAAajgDoAmXgBRtNnR5Kkt2Al47Uet8lcU4sCUeqGbCGTMxATrZA7iFxlIrSDkWBtK8dCK3QLZCztJp6zzlvq3WZAl8N2R3L6qKYgyCeLLHGJA3POkZAbZASiZAypDqy31BABFBAVZAQ5djCBnZA3ckGZBNf7ZBkS2ZBZBA4730qJM1RP4ZBSkYQUzFpIzBMZA3VXQs1ugxhT5sG24K4n4OWDOz62VWPMvZAxhQEIMyHdTdouosXNaYHsDxnAAqmcUG0v5iPPYyAk529NVOJqMfM77zosqggEkeJ4ZCmxI2LZAv0mgmuZCf"

OLD_FAKE_FB_ID = "100000000000001"


async def seed() -> None:
    async with AsyncSessionFactory() as session:

        old_fb = await session.execute(
            select(FacebookAccount).where(
                FacebookAccount.facebook_user_id == OLD_FAKE_FB_ID
            )
        )
        old_fb_account = old_fb.scalar_one_or_none()
        if old_fb_account:
            await session.delete(old_fb_account)
            await session.flush()
            print(f"[CLEAN]  Removed old fake Facebook account ({OLD_FAKE_FB_ID})")

        # ── User ──────────────────────────────────────────────────────────────
        # Check by email (case-insensitive)
        result = await session.execute(
            select(User).where(User.email.ilike(SEED_EMAIL))
        )
        user = result.scalar_one_or_none()

        if user:
            user.full_name      = SEED_FULL_NAME
            user.profile_picture = SEED_PROFILE_PIC
            user.hashed_password = hash_password(SEED_PASSWORD)
            user.is_active       = True
            await session.flush()
            print(f"[UPDATE] User updated: {user.email} (id={user.id})")
        else:
            user = User(
                id=uuid.uuid4(),
                email=SEED_EMAIL,
                hashed_password=hash_password(SEED_PASSWORD),
                full_name=SEED_FULL_NAME,
                profile_picture=SEED_PROFILE_PIC,
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            await session.flush()
            print(f"[OK]     Created user: {user.email} (id={user.id})")

        # ── Facebook Account ──────────────────────────────────────────────────
        fb_result = await session.execute(
            select(FacebookAccount).where(
                FacebookAccount.facebook_user_id == SEED_FB_USER_ID
            )
        )
        fb_account = fb_result.scalar_one_or_none()

        encrypted_token = encrypt_token(PLACEHOLDER_TOKEN)

        if fb_account:
            fb_account.user_id             = user.id
            fb_account.name                = SEED_FULL_NAME
            fb_account.email               = SEED_EMAIL
            fb_account.profile_picture     = SEED_PROFILE_PIC
            fb_account.access_token_encrypted = encrypted_token
            fb_account.long_lived_token_encrypted = encrypted_token
            fb_account.is_active           = True
            await session.flush()
            print(f"[UPDATE] Facebook account updated: {SEED_FB_USER_ID}")
        else:
            fb_account = FacebookAccount(
                id=uuid.uuid4(),
                user_id=user.id,
                facebook_user_id=SEED_FB_USER_ID,
                name=SEED_FULL_NAME,
                email=SEED_EMAIL,
                profile_picture=SEED_PROFILE_PIC,
                access_token_encrypted=encrypted_token,
                long_lived_token_encrypted=encrypted_token,
                is_active=True,
            )
            session.add(fb_account)
            await session.flush()
            print(f"[OK]     Created Facebook account: {SEED_FB_USER_ID}")

        # ── Ad Account ────────────────────────────────────────────────────────
        ad_result = await session.execute(
            select(AdAccount).where(
                AdAccount.account_id == SEED_AD_ACCOUNT_ID
            )
        )
        ad_account = ad_result.scalar_one_or_none()

        if ad_account:
            ad_account.facebook_account_id = fb_account.id
            ad_account.user_id = user.id
            ad_account.account_name = "Test Ad Account"
            ad_account.is_active = True
            await session.flush()
            print(f"[UPDATE] Ad account updated: {SEED_AD_ACCOUNT_ID}")
        else:
            ad_account = AdAccount(
                id=uuid.uuid4(),
                facebook_account_id=fb_account.id,
                user_id=user.id,
                account_id=SEED_AD_ACCOUNT_ID,
                account_name="Test Ad Account",
                currency="USD",
                timezone="UTC",
                account_status=1,
                is_active=True,
            )
            session.add(ad_account)
            await session.flush()
            print(f"[OK]     Created Ad account: {SEED_AD_ACCOUNT_ID}")

        # 4. Upsert Facebook Page
        page_result = await session.execute(
            select(FacebookPage).where(
                FacebookPage.page_id == SEED_FB_PAGE_ID
            )
        )
        fb_page = page_result.scalar_one_or_none()
        if fb_page:
            fb_page.facebook_account_id = fb_account.id
            fb_page.user_id = user.id
            fb_page.name = "Test FB Page"
            fb_page.page_access_token_encrypted = encrypted_token
            await session.flush()
            print(f"[UPDATE] Facebook Page updated: {SEED_FB_PAGE_ID}")
        else:
            fb_page = FacebookPage(
                id=uuid.uuid4(),
                user_id=user.id,
                facebook_account_id=fb_account.id,
                page_id=SEED_FB_PAGE_ID,
                name="Test FB Page",
                page_access_token_encrypted=encrypted_token,
                is_active=True,
            )
            session.add(fb_page)
            await session.flush()
            print(f"[OK]     Created Facebook Page: {SEED_FB_PAGE_ID}")

        # 5. Upsert Instagram Account
        ig_result = await session.execute(
            select(InstagramAccount).where(
                InstagramAccount.instagram_account_id == SEED_INSTAGRAM_ACCOUNT_ID
            )
        )
        ig_account = ig_result.scalar_one_or_none()
        if ig_account:
            ig_account.facebook_page_id = fb_page.id
            ig_account.user_id = user.id
            ig_account.username = "test_instagram"
            ig_account.access_token = encrypted_token
            await session.flush()
            print(f"[UPDATE] Instagram account updated: {SEED_INSTAGRAM_ACCOUNT_ID}")
        else:
            ig_account = InstagramAccount(
                id=uuid.uuid4(),
                user_id=user.id,
                facebook_page_id=fb_page.id,
                instagram_account_id=SEED_INSTAGRAM_ACCOUNT_ID,
                username="test_instagram",
                access_token=encrypted_token,
            )
            session.add(ig_account)
            await session.flush()
            print(f"[OK]     Created Instagram account: {SEED_INSTAGRAM_ACCOUNT_ID}")

        await session.commit()

        # ── Print summary ─────────────────────────────────────────────────────
        access_token  = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        print()
        print("=" * 65)
        print("  SEED COMPLETE — Your real Facebook data is loaded")
        print("=" * 65)
        print(f"  Name          : {SEED_FULL_NAME}")
        print(f"  Email         : {SEED_EMAIL}")
        print(f"  Password      : {SEED_PASSWORD}")
        print(f"  Facebook ID   : {SEED_FB_USER_ID}")
        print(f"  User ID (DB)  : {user.id}")
        print(f"  FB Acct (DB)  : {fb_account.id}")
        print(f"  Ad Acct (DB)  : {ad_account.id}   <--- USE THIS IN YOUR CAMPAIGN CURL")
        print()
        print("  ── Login with email/password ───────────────────────────")
        print(f'  curl -s -X POST http://localhost:8000/api/v1/auth/login \\')
        print(f'       -H "Content-Type: application/json" \\')
        print(f'       -d \'{{"email":"{SEED_EMAIL}","password":"{SEED_PASSWORD}"}}\'')
        print()
        print("  ── Or login with Facebook OAuth ────────────────────────")
        print("  GET  http://localhost:8000/api/v1/auth/facebook/login")
        print("       → open the oauth_url in your browser")
        print("       → completes with a real token linked to your FB ID")
        print()
        print("  ── Pre-generated Access Token (60 min) ─────────────────")
        print(f"  {access_token}")
        print()
        print("  ── Pre-generated Refresh Token (30 days) ───────────────")
        print(f"  {refresh_token}")
        print()
        print("  ── Test /me ─────────────────────────────────────────────")
        print(f'  curl -s -H "Authorization: Bearer {access_token}" \\')
        print(f'       http://localhost:8000/api/v1/auth/me')
        print("=" * 65)
        print()
        print("  NOTE: The Facebook access token is a placeholder.")
        print("  Complete the OAuth flow at /api/v1/auth/facebook/login")
        print("  to replace it with a real token for API calls.")
        print("=" * 65)


if __name__ == "__main__":
    asyncio.run(seed())
