import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from app.core.database import Base

class MessageSender(str, enum.Enum):
    USER = "user"
    AI = "ai"
    ADMIN = "admin"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    TEMPLATE = "template" # for Meta pre-approved templates

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    customer_phone = Column(String, index=True, nullable=False) # Linked by phone, not necessarily foreign key if guest
    sender = Column(String, nullable=False) # 'user', 'ai' or 'admin'
    message_type = Column(String, default="text") # 'text', 'image', 'audio', 'template'
    content = Column(Text, nullable=True) # Text content or Image URL
    created_at = Column(DateTime, default=datetime.utcnow)


    # Optional: Link to Customer if they exist in our DB
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    # customer = relationship("Customer")

class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    customer_phone = Column(String, index=True, nullable=True)
    endpoint = Column(String, default="gemini") # or any other provider marker
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
