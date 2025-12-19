from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# Token Generation
class TokenInfo(BaseModel):
    customer_id: int
    customer_name: str
    access_token: str
    access_url: str
    
    model_config = {"from_attributes": True}


class GenerateTokensResponse(BaseModel):
    sale_id: int
    sale_date: str
    tokens: List[TokenInfo]
    total_customers: int


# Public Order Schemas
class ProductInfo(BaseModel):
    id: int
    name: str
    description: Optional[str]
    sell_price: float
    
    model_config = {"from_attributes": True}


class OrderItemInput(BaseModel):
    product_id: int
    quantity: int


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float


class PublicOrderView(BaseModel):
    # Sale info
    sale_id: int
    sale_date: str
    sale_status: str
    is_open: bool  # Can customer edit?
    
    # Customer info
    customer_id: int
    customer_name: str
    
    # Available products
    available_products: List[ProductInfo]
    
    # Customer's current order
    current_order: List[OrderItemResponse]
    order_total: float
    
    # Messages
    message: Optional[str] = None


class SaveOrderRequest(BaseModel):
    items: List[OrderItemInput]


class SaveOrderResponse(BaseModel):
    success: bool
    message: str
    order_total: float
    items_count: int
