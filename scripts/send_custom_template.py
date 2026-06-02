import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.services.whatsapp import WhatsAppService
from app.core.config import settings

logging.basicConfig(level=logging.INFO)

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def send_custom():
    async with AsyncSessionLocal() as session:
        # Fetch the contact
        result = await session.execute(
            text("SELECT full_name, mobile_number FROM whatsapp_contacts WHERE mobile_number = '6376082733' LIMIT 1")
        )
        contact = result.fetchone()
        
        if not contact:
            print("Contact not found!")
            return
            
        print(f"Loaded Contact: {contact.full_name} ({contact.mobile_number})")

        # In a real scenario, you'd fetch the template from the DB
        # template = ...
        # variables = template.variables # e.g. ["full_name", "mobile_number"]
        
        # Simulating the variables mapping based on your request:
        # "Hi {{1}}, your phone number is {{2}}"
        
        # Meta API requires parameters in exact order of {{1}}, {{2}}...
        components = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": contact.full_name},     # Maps to {{1}}
                    {"type": "text", "text": contact.mobile_number}, # Maps to {{2}}
                ]
            }
        ]

        service = WhatsAppService()
        
        # NOTE: You MUST create and approve a template named 'contact_info_demo' 
        # in your Meta WhatsApp Manager with the body: "Hi {{1}}, your phone number is {{2}}" 
        # BEFORE this will successfully send.
        
        # If 'contact_info_demo' is not yet approved in your Meta App, 
        # this request will fail with an API Error from Meta.
        
        try:
            response = await service.send_template_message(
                to_number="916376082733", # Including country code 91
                template_name="contact_info_demo", # Must match the exact name in Meta
                components=components,
            )
            print("Success:", response)
        except Exception as e:
            print("\n--- META API ERROR ---")
            print("Failed to send because the template 'contact_info_demo' does not exist or is not approved in your Meta WhatsApp Manager yet.")
            print(f"Error Message: {e}")
            if hasattr(e, 'response'):
                print(f"Meta Response: {e.response.text}")

if __name__ == "__main__":
    asyncio.run(send_custom())
