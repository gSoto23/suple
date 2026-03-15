import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def clean_marketing():
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM campaign_recipients"))
        await session.execute(text("DELETE FROM campaigns"))
        await session.execute(text("DELETE FROM marketing_templates"))
        await session.commit()
        print("Marketing data successfully cleaned!")

if __name__ == "__main__":
    asyncio.run(clean_marketing())
