from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True, nullable=False)
    phone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    ai_active = Column(Boolean, default=True)
    address = Column(String, nullable=True)
    addresses = Column(JSON, nullable=True)  # List of address objects
    default_payment_method = Column(String, nullable=True) # Tarjeta, Transferencia, Sinpe, Efectivo
    
    # New specific fields for Supplements Business
    goal = Column(String, nullable=True) # e.g., "Ganar masa muscular", "Perder peso"
    training_days = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    medical_data = Column(Text, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = relationship("Order", back_populates="customer", lazy="selectin")
    subscriptions = relationship("Subscription", back_populates="customer", lazy="selectin")
