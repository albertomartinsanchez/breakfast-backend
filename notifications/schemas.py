from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeviceRegisterRequest(BaseModel):
    device_token: str
    device_type: str  # 'android', 'ios', 'web'


class DeviceRegisterResponse(BaseModel):
    success: bool
    message: str


class DeviceUnregisterRequest(BaseModel):
    device_token: str


class PushDeviceResponse(BaseModel):
    id: int
    device_type: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True
