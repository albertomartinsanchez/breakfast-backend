from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import date

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class CustomerSaleCreate(BaseModel):
    customer_id: int
    products: List[SaleItemCreate]

class SaleCreate(BaseModel):
    date: date
    customer_sales: List[CustomerSaleCreate]

class SaleItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    buy_price_at_sale: float
    sell_price_at_sale: float
    benefit: float
    model_config = ConfigDict(from_attributes=True)

class CustomerSaleResponse(BaseModel):
    customer_id: int
    customer_name: str
    products: List[SaleItemResponse]
    total_benefit: float
    total_revenue: float

class SaleResponse(BaseModel):
    id: int
    user_id: int
    date: date
    status: str    
    customer_sales: List[CustomerSaleResponse]
    total_benefit: float
    total_revenue: float
    model_config = ConfigDict(from_attributes=True)

class SaleUpdate(BaseModel):
    date: date
    customer_sales: List[CustomerSaleCreate]

# ============================================================================
# DELIVERY SCHEMAS (Phase 1)
# ============================================================================

from typing import Optional, Literal
from datetime import datetime

class CustomerSequence(BaseModel):
    """Schema for reordering delivery route"""
    customer_id: int
    sequence: int


class DeliveryStepResponse(BaseModel):
    id: int
    sale_id: int
    customer_id: int
    customer_name: str
    sequence_order: int
    status: str
    is_next: bool = False
    completed_at: Optional[datetime] = None
    amount_collected: Optional[float] = None
    credit_applied: Optional[float] = None
    skip_reason: Optional[str] = None
    total_amount: float
    customer_credit: float = 0.0
    credit_to_apply: float = 0.0
    amount_to_collect: float = 0.0
    items: List[dict]

    model_config = ConfigDict(from_attributes=True)


class DeliveryStepUpdate(BaseModel):
    """Schema for updating a delivery step (select as next, complete, skip, reset)"""
    is_next: Optional[bool] = None
    status: Optional[Literal["pending", "completed", "skipped"]] = None
    amount_collected: Optional[float] = None
    skip_reason: Optional[str] = None


class DeliveryProgressResponse(BaseModel):
    total_deliveries: int
    completed_count: int
    pending_count: int
    skipped_count: int
    total_collected: float
    total_credit_applied: float = 0.0
    total_expected: float
    total_skipped_amount: float
    current_delivery: Optional[DeliveryStepResponse] = None
    pending_deliveries: List[DeliveryStepResponse] = []
