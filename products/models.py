from sqlalchemy import Column, Integer, String, Float
from core.database import Base


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=False)
