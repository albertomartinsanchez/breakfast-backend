from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class Customer(Base):
    __tablename__ = "customer"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String)
    phone = Column(String)
    credit = Column(Float, default=0.0, nullable=False)
    user = relationship("User")
    access_token = relationship("CustomerAccessToken", back_populates="customer", uselist=False, cascade="all, delete-orphan")
