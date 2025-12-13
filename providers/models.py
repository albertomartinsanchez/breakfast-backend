from sqlalchemy import Column, Integer, String
from core.database import Base


class Provider(Base):
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String)
    address = Column(String)
