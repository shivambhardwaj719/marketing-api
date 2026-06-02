import httpx
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v21.0/{self.phone_number_id}/messages"

    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        language_code: str = "en_US",
        components: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Send a WhatsApp template message.
        """
        if not self.access_token or not self.phone_number_id:
            logger.error("WhatsApp credentials not configured")
            raise ValueError("WhatsApp credentials not configured in environment")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=10.0,
            )
            if not response.is_success:
                error_body = response.json()
                logger.error("WhatsApp API error %s: %s", response.status_code, error_body)
                raise ValueError(error_body)
            return response.json()
