from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, JSON
from datetime import datetime
from app.core.database import Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    
    # General Business info
    business_name = Column(String, default="Mi Negocio")
    store_addresses = Column(JSON, default=list) 
    account_number = Column(String, nullable=True)
    sinpe_number = Column(String, nullable=True)
    customer_service_phone = Column(String, nullable=True)
    
    # Feature Toggles
    enable_subscriptions = Column(Boolean, default=True, nullable=False)
    enable_marketing = Column(Boolean, default=True, nullable=False)
    
    # Existing settings from InventoryConfig
    subscription_discount_percentage = Column(Numeric(5, 2), default=0.0)
    min_subscription_duration_days = Column(Integer, default=0)
    
    # Premium customizations
    currency_symbol = Column(String, default="₡")
    country_phone_code = Column(String, default="506")
    company_icon_class = Column(String, default="fa-solid fa-dumbbell")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
