from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class Sale(Base):
    __tablename__ = "sale"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_item"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_price_at_sale = Column(Float, nullable=False)
    sell_price_at_sale = Column(Float, nullable=False)
    sale = relationship("Sale", back_populates="items")
    customer = relationship("Customer")
    product = relationship("Product")
