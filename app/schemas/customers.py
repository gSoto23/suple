from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional, List, Any
from datetime import datetime
import os

# Subscription Schemas (Forward declaration if needed, or simple dict for now)
class SubscriptionBasic(BaseModel):
    id: int
    product_id: int
    status: str
    next_billing_date: datetime
    
    class Config:
        from_attributes = True

# Customer Schemas
class CustomerBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: bool = True
    ai_active: bool = True
    address: Optional[str] = None
    addresses: Optional[List[dict]] = None
    default_payment_method: Optional[str] = None
    goal: Optional[str] = None
    training_days: Optional[int] = None
    age: Optional[int] = None
    medical_data: Optional[str] = None
    notes: Optional[str] = None

class CustomerBasic(CustomerBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    ai_active: Optional[bool] = None
    address: Optional[str] = None
    addresses: Optional[List[dict]] = None
    default_payment_method: Optional[str] = None
    goal: Optional[str] = None
    training_days: Optional[int] = None
    age: Optional[int] = None
    medical_data: Optional[str] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Juan Perez",
                "phone": "88888888",
                "goal": "Ganar masa muscular",
                "training_days": 4,
                "is_active": True
            }
        }
    }

class CustomerOrderItemProduct(BaseModel):
    name: str

class CustomerOrderItem(BaseModel):
    product: Optional[CustomerOrderItemProduct] = None
    quantity: int
    unit_price_at_moment: float
    subtotal: float
    
    class Config:
        from_attributes = True

class CustomerOrder(BaseModel):
    id: int
    total_amount: float
    status: str
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None
    delivery_address: Optional[str] = None
    created_at: datetime
    items: List[CustomerOrderItem] = []
    
    @computed_field
    @property
    def has_payment_receipt(self) -> bool:
        return bool(self.payment_proof)
        
    @computed_field
    @property
    def payment_receipt_url(self) -> Optional[str]:
        if not self.payment_proof:
            return None
        return f"/api/orders/{self.id}/receipt"

    
    class Config:
        from_attributes = True

class CustomerInteraction(BaseModel):
    sender: str
    message_type: str
    content: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    subscriptions: List[SubscriptionBasic] = []
    orders: List[CustomerOrder] = []
    recent_interactions: List[CustomerInteraction] = []
    
    class Config:
        from_attributes = True
