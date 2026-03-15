import enum
from sqlalchemy import Column, Integer, String, Text, DateTime
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
