import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def add_template():
    async with AsyncSessionLocal() as session:
        # Get first user for association
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = result.scalar()
        
        if not user_id:
            print("No users found in database.")
            return

        # Add the whatsapp template
        template_id = uuid.uuid4()
        
        # We store the variables array mapping to Meta's {{1}} and {{2}}
        variables = ["full_name", "mobile_number"]
        
        await session.execute(text(
            """
            INSERT INTO whatsapp_templates 
            (id, user_id, template_name, category, language, body, variables, status, created_at, updated_at) 
            VALUES 
            (:id, :user_id, 'contact_info_demo', 'UTILITY', 'en_US', 'Hi {{1}}, your phone number is {{2}}.', :variables, 'APPROVED', now(), now())
            """
        ), {
            "id": template_id, 
            "user_id": user_id,
            "variables": '["full_name", "mobile_number"]'
        })
        
        await session.commit()
        print(f"Added template 'contact_info_demo' to database.")

if __name__ == "__main__":
    asyncio.run(add_template())
