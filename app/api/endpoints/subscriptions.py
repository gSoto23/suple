from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Subscription, User
from app.schemas import subscriptions
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[subscriptions.Subscription])
async def read_subscriptions(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[int] = None,
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Subscription)
    if customer_id:
        query = query.where(Subscription.customer_id == customer_id)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=subscriptions.Subscription)
async def create_subscription(
    subscription_in: subscriptions.SubscriptionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    db_subscription = Subscription(**subscription_in.model_dump())
    db.add(db_subscription)
    await db.commit()
    await db.refresh(db_subscription)
    return db_subscription

@router.put("/{sub_id}", response_model=subscriptions.Subscription)
async def update_subscription(
    sub_id: int,
    sub_in: subscriptions.SubscriptionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    update_data = sub_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)
        
    await db.commit()
    await db.refresh(subscription)
    return subscription

@router.delete("/{sub_id}")
async def delete_subscription(
    sub_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    subscription = result.scalars().first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
        
    await db.delete(subscription)
    await db.commit()
    return {"message": "Subscription deleted successfully"}
