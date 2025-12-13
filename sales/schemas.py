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
    customer_sales: List[CustomerSaleResponse]
    total_benefit: float
    total_revenue: float
    model_config = ConfigDict(from_attributes=True)

class SaleUpdate(BaseModel):
    date: date
    customer_sales: List[CustomerSaleCreate]
