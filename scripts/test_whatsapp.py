import asyncio
import logging
from app.services.whatsapp import WhatsAppService
from app.core.config import settings

logging.basicConfig(level=logging.INFO)

async def test_send():
    service = WhatsAppService()
    try:
        response = await service.send_template_message(
            to_number="916376082733",
            template_name="jaspers_market_order_confirmation_v1",
            components=[
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "John Doe"},
                        {"type": "text", "text": "123456"},
                        {"type": "text", "text": "Jun 1, 2026"},
                    ],
                }
            ],
        )
        print("Success:", response)
    except Exception as e:
        print("Error:", e)
        if hasattr(e, 'response'):
            print("Response:", e.response.text)

if __name__ == "__main__":
    asyncio.run(test_send())
