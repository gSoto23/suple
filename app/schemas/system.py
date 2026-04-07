from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class SystemConfigBase(BaseModel):
    # General Business info
    business_name: Optional[str] = "Mi Negocio"
    store_addresses: Optional[List[Dict[str, Any]]] = []
    account_number: Optional[str] = None
    sinpe_number: Optional[str] = None
    customer_service_phone: Optional[str] = None
    
    # Feature Toggles
    enable_subscriptions: Optional[bool] = True
    enable_marketing: Optional[bool] = True
    
    # Existing settings
    subscription_discount_percentage: Optional[float] = 0.0
    min_subscription_duration_days: Optional[int] = 0
    
    # Premium customizations
    currency_symbol: Optional[str] = "₡"
    country_phone_code: Optional[str] = "506"
    company_icon_class: Optional[str] = "fa-solid fa-dumbbell"
    company_theme_color: Optional[str] = "#6b7280"
    
    # AI System
    ai_system_prompt: Optional[str] = "Eres un asistente muy util para ventas de nuestra tienda."
    google_gemini_api_key: Optional[str] = None
    ai_model_name: Optional[str] = "gemini-1.5-flash"

class SystemConfigCreate(SystemConfigBase):
    pass

class SystemConfigUpdate(SystemConfigBase):
    pass

class SystemConfig(SystemConfigBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True
