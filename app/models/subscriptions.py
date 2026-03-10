import sqlalchemy as sa
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    customer_id = sa.Column(sa.Integer, sa.ForeignKey("customers.id"), nullable=False)
    product_id = sa.Column(sa.Integer, sa.ForeignKey("products.id"), nullable=False)
    
    quantity = sa.Column(sa.Integer, default=1, nullable=False)
    frequency_days = sa.Column(sa.Integer, nullable=False) # e.g., 30 for monthly
    status = sa.Column(sa.String, default="active", index=True) # active, paused, cancelled
    
    next_billing_date = sa.Column(sa.DateTime, nullable=False)
    applied_discount = sa.Column(sa.Numeric(5, 2), default=0.0)
    min_duration_days = sa.Column(sa.Integer, default=0)
    notes = sa.Column(sa.Text, nullable=True)
    
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="subscriptions")
    product = relationship("Product", back_populates="subscriptions")
    orders = relationship("Order", back_populates="subscription")
