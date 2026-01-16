from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)

class CustomerCreate(CustomerBase):
    credit: Optional[float] = Field(0.0, ge=0)

class CustomerUpdate(CustomerBase):
    credit: Optional[float] = Field(None, ge=0)

class AccessTokenResponse(BaseModel):
    access_token: str

class CustomerResponse(CustomerBase):
    id: int
    user_id: int
    credit: float = 0.0
    access_token: Optional[AccessTokenResponse] = None