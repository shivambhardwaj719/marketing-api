import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def add_contact():
    async with AsyncSessionLocal() as session:
        # Get first user for association
        result = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = result.scalar()
        
        if not user_id:
            print("No users found in database, creating a dummy user...")
            user_id = uuid.uuid4()
            await session.execute(text(
                "INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at) "
                "VALUES (:id, 'admin@example.com', 'dummy', true, now(), now())"
            ), {"id": user_id})
            await session.commit()
            
        # Check if contact exists
        result = await session.execute(text("SELECT id FROM whatsapp_contacts WHERE mobile_number = '6376082733'"))
        existing = result.scalar()
        if existing:
            print("Contact 6376082733 already exists.")
        else:
            # Add the whatsapp contact
            contact_id = uuid.uuid4()
            await session.execute(text(
                "INSERT INTO whatsapp_contacts (id, user_id, full_name, country_code, mobile_number, status, created_at, updated_at) "
                "VALUES (:id, :user_id, 'Test Contact', '91', '6376082733', 'ACTIVE', now(), now())"
            ), {"id": contact_id, "user_id": user_id})
            await session.commit()
            print(f"Added contact 6376082733 to database.")

if __name__ == "__main__":
    asyncio.run(add_contact())
