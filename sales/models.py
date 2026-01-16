from sqlalchemy import Column, Integer, Float, Date, String, ForeignKey, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from core.database import Base

class Sale(Base):
    __tablename__ = "sale"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="draft", nullable=False)  # NEW: draft, closed, in_progress, completed
    
    user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    delivery_steps = relationship("SaleDeliveryStep", back_populates="sale", cascade="all, delete-orphan", order_by="SaleDeliveryStep.sequence_order")  # NEW

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

# NEW MODEL
class SaleDeliveryStep(Base):
    __tablename__ = "sale_delivery_step"
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    sequence_order = Column(Integer, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, completed, skipped
    is_next = Column(Boolean, default=False, nullable=False)  # True if selected as next delivery
    completed_at = Column(DateTime, nullable=True)
    amount_collected = Column(Float, nullable=True)
    skip_reason = Column(String, nullable=True)
    
    sale = relationship("Sale", back_populates="delivery_steps")
    customer = relationship("Customer")
    
    __table_args__ = (
        UniqueConstraint('sale_id', 'customer_id', name='unique_sale_customer'),
        UniqueConstraint('sale_id', 'sequence_order', name='unique_sale_sequence'),
    )
