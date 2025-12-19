from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


class CustomerAccessToken(Base):
    __tablename__ = "customer_access_token"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, unique=True)
    access_token = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="access_token")
