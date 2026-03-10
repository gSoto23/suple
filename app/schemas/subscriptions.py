from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SubscriptionBase(BaseModel):
    customer_id: int
    product_id: int
    quantity: int = 1
    frequency_days: int
    status: str = "active"
    next_billing_date: datetime
    applied_discount: float = 0.0
    min_duration_days: int = 0
    notes: Optional[str] = None

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    quantity: Optional[int] = None
    frequency_days: Optional[int] = None
    status: Optional[str] = None
    next_billing_date: Optional[datetime] = None
    applied_discount: Optional[float] = None
    min_duration_days: Optional[int] = None
    notes: Optional[str] = None

class Subscription(SubscriptionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
