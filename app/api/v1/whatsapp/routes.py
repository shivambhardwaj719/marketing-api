import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.deps import get_current_user, get_db, DBSession
from app.models.user import User
from app.models.whatsapp import WhatsAppContact, WhatsAppTemplate, WhatsAppCampaign, WhatsAppCampaignContact
from app.schemas.whatsapp import (
    WhatsAppContactCreate,
    WhatsAppContactUpdate,
    WhatsAppContactResponse,
    WhatsAppTemplateCreate,
    WhatsAppTemplateUpdate,
    WhatsAppTemplateResponse,
    WhatsAppCampaignCreate,
    WhatsAppCampaignResponse,
)
from app.services.whatsapp import WhatsAppService

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

@router.post("/test-send")
async def test_send_message(
    to_number: str = "916376082733",
    current_user: User = Depends(get_current_user),
) -> Any:
    service = WhatsAppService()
    try:
        response = await service.send_template_message(
            to_number=to_number,
            template_name="jaspers_market_order_confirmation_v1",
            components=[
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "Test User"},
                        {"type": "text", "text": "123456"},
                        {"type": "text", "text": "Jun 1, 2026"},
                    ],
                }
            ],
        )
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Contacts ---

@router.post("/contacts", response_model=WhatsAppContactResponse)
async def create_contact(
    data: WhatsAppContactCreate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    contact = WhatsAppContact(**data.model_dump(), user_id=current_user.id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact

@router.get("/contacts", response_model=list[WhatsAppContactResponse])
async def get_contacts(
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppContact).where(WhatsAppContact.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/contacts/{contact_id}", response_model=WhatsAppContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppContact).where(WhatsAppContact.id == contact_id, WhatsAppContact.user_id == current_user.id)
    contact = (await db.execute(stmt)).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact

@router.put("/contacts/{contact_id}", response_model=WhatsAppContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    data: WhatsAppContactUpdate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppContact).where(WhatsAppContact.id == contact_id, WhatsAppContact.user_id == current_user.id)
    contact = (await db.execute(stmt)).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
        
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact

@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppContact).where(WhatsAppContact.id == contact_id, WhatsAppContact.user_id == current_user.id)
    contact = (await db.execute(stmt)).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    await db.delete(contact)
    await db.commit()
    return {"status": "success", "message": "Contact deleted"}

# --- Templates ---

@router.post("/templates", response_model=WhatsAppTemplateResponse)
async def create_template(
    data: WhatsAppTemplateCreate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    template = WhatsAppTemplate(**data.model_dump(), user_id=current_user.id)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.get("/templates", response_model=list[WhatsAppTemplateResponse])
async def get_templates(
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/templates/{template_id}", response_model=WhatsAppTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/templates/{template_id}", response_model=WhatsAppTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: WhatsAppTemplateUpdate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
        
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    await db.delete(template)
    await db.commit()
    return {"status": "success", "message": "Template deleted"}

@router.get("/templates/{template_id}", response_model=WhatsAppTemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/templates/{template_id}", response_model=WhatsAppTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: WhatsAppTemplateUpdate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
        
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
        
    await db.delete(template)
    await db.commit()
    return {"status": "success", "message": "Template deleted"}

# --- Campaigns ---

@router.post("/campaigns", response_model=WhatsAppCampaignResponse)
async def create_campaign(
    data: WhatsAppCampaignCreate,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    from sqlalchemy.exc import IntegrityError
    
    # 1. Fetch the template first to get its name
    stmt_tmpl = select(WhatsAppTemplate).where(WhatsAppTemplate.id == data.template_id, WhatsAppTemplate.user_id == current_user.id)
    template = (await db.execute(stmt_tmpl)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=400, detail="Template not found")
        
    campaign_data = data.model_dump(exclude={"contact_ids"})
    campaign = WhatsAppCampaign(**campaign_data, user_id=current_user.id)
    db.add(campaign)
    
    try:
        await db.flush()

        wa_service = WhatsAppService()
        send_results = []

        for contact_id in data.contact_ids:
            cc = WhatsAppCampaignContact(campaign_id=campaign.id, contact_id=contact_id)
            db.add(cc)

            stmt_contact = select(WhatsAppContact).where(WhatsAppContact.id == contact_id, WhatsAppContact.user_id == current_user.id)
            contact = (await db.execute(stmt_contact)).scalar_one_or_none()

            if contact:
                full_number = f"{contact.country_code or ''}{contact.mobile_number}"
                
                if template.template_name == "hello_world":
                    components = None
                else:
                    components = [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": contact.full_name or "Valued Customer"},
                                {"type": "text", "text": full_number},
                            ],
                        }
                    ]

                try:
                    fb_response = await wa_service.send_template_message(
                        to_number=full_number,
                        template_name=template.template_name,
                        components=components
                    )
                    cc.message_status = "SENT"
                    send_results.append({
                        "contact_id": str(contact_id),
                        "phone": full_number,
                        "status": "sent",
                        "facebook_response": fb_response,
                    })
                except Exception as e:
                    logger.error("Failed to send WhatsApp message to %s: %s", full_number, e)
                    cc.message_status = "FAILED"
                    cc.failure_reason = str(e)
                    send_results.append({
                        "contact_id": str(contact_id),
                        "phone": full_number,
                        "status": "failed",
                        "facebook_response": e.args[0] if e.args else str(e),
                    })
            else:
                send_results.append({
                    "contact_id": str(contact_id),
                    "phone": None,
                    "status": "skipped",
                    "facebook_response": "Contact not found or does not belong to this user",
                })

        await db.commit()
        await db.refresh(campaign)

        campaign_dict = {
            "campaign_name": campaign.campaign_name,
            "description": campaign.description,
            "campaign_type": campaign.campaign_type,
            "template_id": str(campaign.template_id),
            "scheduled_at": campaign.scheduled_at,
            "id": str(campaign.id),
            "user_id": str(campaign.user_id),
            "status": campaign.status,
            "started_at": campaign.started_at,
            "completed_at": campaign.completed_at,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
            "send_results": send_results,
        }
        return campaign_dict
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid template_id or contact_id provided. Make sure they exist."
        )

@router.get("/campaigns", response_model=list[WhatsAppCampaignResponse])
async def get_campaigns(
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppCampaign).where(WhatsAppCampaign.user_id == current_user.id)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/campaigns/{campaign_id}", response_model=WhatsAppCampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppCampaign).where(WhatsAppCampaign.id == campaign_id, WhatsAppCampaign.user_id == current_user.id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: uuid.UUID,
    db: DBSession,
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(WhatsAppCampaign).where(WhatsAppCampaign.id == campaign_id, WhatsAppCampaign.user_id == current_user.id)
    campaign = (await db.execute(stmt)).scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    await db.delete(campaign)
    await db.commit()
    return {"status": "success", "message": "Campaign deleted"}
