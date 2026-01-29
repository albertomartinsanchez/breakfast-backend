from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from core.encrypted_type import EncryptedString


class Customer(Base):
    __tablename__ = "customer"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    # Encrypted fields
    name = Column(EncryptedString, nullable=False)
    address = Column(EncryptedString)
    phone = Column(EncryptedString)
    # Blind index for searchable name (HMAC of lowercase name)
    name_index = Column(String, index=True)
    credit = Column(Float, default=0.0, nullable=False)
    user = relationship("User")
    access_token = relationship("CustomerAccessToken", back_populates="customer", uselist=False, cascade="all, delete-orphan")
