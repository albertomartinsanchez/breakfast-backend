from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    pass

class AccessTokenResponse(BaseModel):
    access_token: str

class CustomerResponse(CustomerBase):
    id: int
    user_id: int
    access_token: Optional[AccessTokenResponse] = None