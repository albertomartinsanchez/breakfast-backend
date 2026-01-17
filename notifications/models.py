from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base


class PushDevice(Base):
    """Stores FCM device tokens for push notifications"""
    __tablename__ = "push_device"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, index=True)
    device_token = Column(String, unique=True, nullable=False, index=True)
    device_type = Column(String, nullable=False)  # 'android', 'ios', 'web'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("Customer", backref="push_devices")
