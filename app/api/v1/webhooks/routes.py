from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, Request, Response

from app.core.config import settings
from app.core.logger import get_logger
from app.schemas.webhook import FacebookWebhookPayload

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get("/facebook")
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """Facebook webhook verification endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN:
        logger.info("facebook_webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("facebook_webhook_verification_failed", token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/facebook", status_code=200)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
):
    """Receive Facebook webhook events (leadgen)."""
    raw_body = await request.body()

    # Signature verification
    if settings.FACEBOOK_APP_SECRET and x_hub_signature_256:
        from app.core.security import verify_facebook_webhook_signature
        if not verify_facebook_webhook_signature(raw_body, x_hub_signature_256):
            logger.warning("invalid_webhook_signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload_dict = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    background_tasks.add_task(_process_webhook_payload, payload_dict, raw_body.decode())
    return {"status": "received"}


async def _process_webhook_payload(payload: dict[str, Any], raw_body: str) -> None:
    """Background task: parse and dispatch leadgen events."""
    from app.core.database import AsyncSessionFactory
    from app.models.webhook_log import WebhookLog
    from app.workers.tasks.lead_tasks import process_lead_from_webhook

    async with AsyncSessionFactory() as session:
        try:
            for entry in payload.get("entry", []):
                page_id = entry.get("id")
                for change in entry.get("changes", []):
                    if change.get("field") != "leadgen":
                        continue
                    value = change.get("value", {})
                    lead_id = value.get("leadgen_id")
                    form_id = value.get("form_id")
                    ad_id = value.get("ad_id")
                    adset_id = value.get("adset_id")
                    campaign_id = value.get("campaign_id")

                    log = WebhookLog(
                        event_type="leadgen",
                        object_type=payload.get("object"),
                        facebook_object_id=page_id,
                        payload=value,
                        raw_body=raw_body,
                        processing_status="pending",
                    )
                    session.add(log)
                    await session.flush()

                    try:
                        process_lead_from_webhook.delay(
                            page_fb_id=page_id,
                            lead_id=lead_id,
                            form_id=form_id,
                            ad_id=ad_id,
                            adset_id=adset_id,
                            campaign_id=campaign_id,
                            webhook_log_id=str(log.id),
                        )
                        log.processing_status = "queued"
                    except Exception as e:
                        log.processing_status = "failed"
                        log.error_message = str(e)
                        logger.exception("failed_to_queue_lead_task", error=str(e))

            await session.commit()
        except Exception as exc:
            await session.rollback()
            logger.exception("webhook_processing_error", error=str(exc))

@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """WhatsApp webhook verification endpoint."""
    if hub_mode == "subscribe" and hub_verify_token == settings.FACEBOOK_WEBHOOK_VERIFY_TOKEN:
        logger.info("whatsapp_webhook_verified")
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("whatsapp_webhook_verification_failed", token=hub_verify_token)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/whatsapp", status_code=200)
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None),
):
    """Receive WhatsApp webhook events (messages, statuses)."""
    raw_body = await request.body()

    # Signature verification
    if settings.FACEBOOK_APP_SECRET and x_hub_signature_256:
        from app.core.security import verify_facebook_webhook_signature
        if not verify_facebook_webhook_signature(raw_body, x_hub_signature_256):
            logger.warning("invalid_whatsapp_webhook_signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    logger.info("whatsapp_webhook_payload", payload=payload)

    # Parse and print detailed WhatsApp events
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # 1. Handle incoming messages (replies from users)
                if "messages" in value:
                    for message in value["messages"]:
                        from_number = message.get("from")
                        msg_type = message.get("type")
                        msg_id = message.get("id")
                        timestamp = message.get("timestamp")
                        
                        if msg_type == "text":
                            text_body = message.get("text", {}).get("body")
                            print(f"\n🟢 [WHATSAPP MESSAGE RECEIVED] From {from_number}: {text_body}\n")
                        else:
                            print(f"\n🟢 [WHATSAPP MEDIA/OTHER RECEIVED] From {from_number} | Type: {msg_type}\n")

                # 2. Handle message statuses (sent, delivered, read, failed)
                if "statuses" in value:
                    for status in value["statuses"]:
                        recipient_id = status.get("recipient_id")
                        status_str = status.get("status") # 'sent', 'delivered', 'read', 'failed'
                        msg_id = status.get("id")
                        timestamp = status.get("timestamp")
                        
                        icon = "🔵"
                        if status_str == "read":
                            icon = "👀"
                        elif status_str == "delivered":
                            icon = "✅"
                        elif status_str == "failed":
                            icon = "❌"
                            
                        print(f"\n{icon} [WHATSAPP STATUS UPDATE] To {recipient_id}: {status_str.upper()} (Msg ID: {msg_id})\n")
                        
    except Exception as e:
        logger.error(f"Error parsing whatsapp message/status: {e}")

    # TODO: Add background task for robust WhatsApp webhook processing (saving to DB)
    
    return {"status": "received"}
