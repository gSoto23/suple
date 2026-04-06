from pydantic import BaseModel, condecimal
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProductBase(BaseModel):
    sku: str
    name: str
    category: str
    brand: Optional[str] = None
    price: condecimal(max_digits=10, decimal_places=2) # type: ignore
    cost: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    stock: int = 0
    min_stock: int = 5
    is_active: bool = True
    image_url: Optional[str] = None
    description: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = {}

class ProductFieldDefinitionBase(BaseModel):
    name: str
    field_type: str
    options: Optional[List[str]] = []
    is_required: Optional[bool] = False
    order: Optional[int] = 0

class ProductFieldDefinitionCreate(ProductFieldDefinitionBase):
    pass

class ProductFieldDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    field_type: Optional[str] = None
    options: Optional[List[str]] = None
    is_required: Optional[bool] = None
    order: Optional[int] = None

class ProductFieldDefinition(ProductFieldDefinitionBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    cost: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    stock: Optional[int] = None
    min_stock: Optional[int] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    inventory: List[Product]

