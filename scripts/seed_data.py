import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models import User, Product
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed():
    async with AsyncSessionLocal() as session:
        # Check if users exist
        from sqlalchemy import select
        result = await session.execute(select(User))
        user = result.scalars().first()
        
        if not user:
            print("Creating default admin user...")
            admin_user = User(
                name="Agente Admin",
                email="admin@sales-ai.com",
                password_hash=pwd_context.hash("admin123"),
                role="admin",
                is_active=True
            )
            session.add(admin_user)
            
            # Create sample product
            print("Creating sample product...")
            product = Product(
                sku="TEST-001",
                name="TestProduct",
                category="General",
                brand="DemoBrand",
                price=1000.00,
                cost=500.00,
                stock=100,
                min_stock=10
            )
            session.add(product)
            
            await session.commit()
            print("Seed data created successfully.")
        else:
            print("Database already seeded.")

if __name__ == "__main__":
    asyncio.run(seed())
