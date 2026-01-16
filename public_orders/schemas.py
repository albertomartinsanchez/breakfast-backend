from pydantic import BaseModel
from typing import List, Optional
from datetime import date


# Public customer view
class PublicSaleListItem(BaseModel):
    id: int
    date: date
    status: str
    is_open: bool  # Can customer order?
    
    model_config = {"from_attributes": True}


class PublicCustomerInfo(BaseModel):
    customer_id: int
    customer_name: str
    sales: List[PublicSaleListItem]
    
    model_config = {"from_attributes": True}


# Public sale detail for ordering
class PublicProduct(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sell_price: float
    
    model_config = {"from_attributes": True}


class PublicOrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class PublicSaleDetail(BaseModel):
    sale_id: int
    sale_date: date
    sale_status: str
    is_open: bool
    customer_id: int
    customer_name: str
    available_products: List[PublicProduct]
    current_order: List[PublicOrderItem]
    order_total: float
    message: Optional[str] = None


# Update order
class OrderItemInput(BaseModel):
    product_id: int
    quantity: int


class UpdateOrderRequest(BaseModel):
    items: List[OrderItemInput]


class UpdateOrderResponse(BaseModel):
    success: bool
    message: str
    order_total: float
    items_count: int

class DeliveryStatusResponse(BaseModel):
    sale_status: str
    customer_delivery_status: str  # pending, completed, skipped
    is_next: bool = False  # True if this customer is selected as next delivery
    position_in_queue: Optional[int] = None
    deliveries_ahead: Optional[int] = None
    estimated_minutes: Optional[int] = None
    completed_at: Optional[str] = None
    amount_collected: Optional[float] = None
    skip_reason: Optional[str] = None