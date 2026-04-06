from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    custom_fields = Column(JSON, default=dict)

    inventory_movements = relationship("InventoryMovement", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    subscriptions = relationship("Subscription", back_populates="product", lazy="selectin")


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(String, nullable=False)  # in, out, adjustment
    quantity = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_movements")
    created_by = relationship("User")

class ProductFieldDefinition(Base):
    __tablename__ = "product_field_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g. "Sabor", "Talla"
    field_type = Column(String, nullable=False) # "text", "number", "select"
    options = Column(JSON, default=list) # e.g. ["Vainilla", "Chocolate"] if type is "select"
    is_required = Column(Boolean, default=False)
    order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


