from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

# --- MarketingTemplate Schemas ---

class MarketingTemplateBase(BaseModel):
    name: str = Field(..., description="Unique name of the template on Meta")
    language: str = Field(default="es")
    category: Optional[str] = Field(default=None, description="e.g., MARKETING, UTILITY")
    status: Optional[str] = Field(default="PENDING", description="e.g., APPROVED, PENDING, REJECTED")
    components: Optional[List[Dict[str, Any]]] = Field(default=None, description="JSON payload defining the template variables and structure")

class MarketingTemplateCreate(MarketingTemplateBase):
    pass

class MarketingTemplateUpdate(MarketingTemplateBase):
    name: Optional[str] = None

class MarketingTemplateInDBBase(MarketingTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MarketingTemplate(MarketingTemplateInDBBase):
    pass

# --- Campaign Schemas ---

class CampaignBase(BaseModel):
    name: str = Field(..., description="Internal name of the campaign")
    template_id: int = Field(..., description="ID of the MarketingTemplate to use")
    status: Optional[str] = Field(default="draft", description="draft, scheduled, running, completed, cancelled")
    variables_mapping: Optional[Dict[str, str]] = Field(default=None, description="Mapping of Meta components indices/names to customer attributes")
    scheduled_at: Optional[datetime] = None

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    variables_mapping: Optional[Dict[str, str]] = None
    scheduled_at: Optional[datetime] = None

class CampaignInDBBase(CampaignBase):
    id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Campaign(CampaignInDBBase):
    pass

# --- CampaignRecipient Schemas ---

class CampaignRecipientBase(BaseModel):
    campaign_id: int
    customer_id: int
    status: Optional[str] = Field(default="pending", description="pending, sent, delivered, read, failed")
    message_id: Optional[str] = None
    error_message: Optional[str] = None

class CampaignRecipientCreate(CampaignRecipientBase):
    pass

class CampaignRecipientUpdate(BaseModel):
    status: Optional[str] = None
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

class CampaignRecipientInDBBase(CampaignRecipientBase):
    id: int
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CampaignRecipient(CampaignRecipientInDBBase):
    pass
