import asyncio
from app.core.database import engine, Base
# Import all models so they register with Base
from app.models.marketing import MarketingTemplate, Campaign, CampaignRecipient
from app.models.customers import Customer
from app.models.users import User

async def create_tables():
    async with engine.begin() as conn:
        print("Creating missing tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Done.")

if __name__ == "__main__":
    asyncio.run(create_tables())
