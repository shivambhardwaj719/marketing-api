import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.deps import CurrentUser, DBSession
from app.models.user import User
from app.schemas.instagram import InstagramAccountResponse
from app.services.instagram_account import InstagramService

router = APIRouter(prefix="/instagram", tags=["Instagram"])


@router.get("/accounts", response_model=list[InstagramAccountResponse])
async def get_instagram_accounts(
    current_user: CurrentUser,
    db: DBSession,
):
    """Get all connected Instagram accounts for the current user."""
    service = InstagramService(db)
    accounts = await service.get_accounts(current_user.id)
    return [InstagramAccountResponse.model_validate(acc) for acc in accounts]


@router.post("/sync/{page_id}", response_model=InstagramAccountResponse)
async def sync_instagram_account(
    page_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    """Sync an Instagram Business account connected to a specific Facebook Page."""
    service = InstagramService(db)
    account = await service.sync_accounts(current_user.id, page_id)
    if not account:
        raise HTTPException(status_code=404, detail="No Instagram Business Account connected to this Page")
    return InstagramAccountResponse.model_validate(account)



