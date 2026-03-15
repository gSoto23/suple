from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class MarketingTemplate(Base):
    __tablename__ = "marketing_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False, unique=True)
    language = Column(String, default="es")
    category = Column(String, nullable=True) # e.g. MARKETING, UTILITY
    status = Column(String, nullable=True) # e.g. APPROVED, PENDING, REJECTED
    components = Column(JSON, nullable=True) # Full JSON payload from Meta
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    campaigns = relationship("Campaign", back_populates="template")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    template_id = Column(Integer, ForeignKey("marketing_templates.id"), nullable=False)
    status = Column(String, default="draft") # draft, scheduled, running, completed, cancelled
    variables_mapping = Column(JSON, nullable=True) # Dict plotting variable names to customer attributes
    
    scheduled_at = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Admin who created it
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    template = relationship("MarketingTemplate", back_populates="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")
    creator = relationship("User")

class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Message Tracking (pending, sent, delivered, read, failed, opted_out)
    status = Column(String, default="pending", index=True)
    message_id = Column(String, nullable=True, index=True) # Meta API reference
    error_message = Column(Text, nullable=True)
    
    # Timing
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="recipients")
    customer = relationship("Customer")
