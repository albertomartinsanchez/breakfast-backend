from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional


class ProviderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class ProviderCreate(ProviderBase):
    pass


class ProviderUpdate(ProviderBase):
    pass


class ProviderResponse(ProviderBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
