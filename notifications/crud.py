from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from notifications.models import PushDevice
from customers.models_access_token import CustomerAccessToken


async def get_customer_id_by_token(db: AsyncSession, token: str) -> Optional[int]:
    """Get customer ID from access token"""
    result = await db.execute(
        select(CustomerAccessToken.customer_id)
        .where(CustomerAccessToken.access_token == token)
    )
    row = result.scalar_one_or_none()
    return row


async def register_device(
    db: AsyncSession,
    customer_id: int,
    device_token: str,
    device_type: str
) -> PushDevice:
    """Register or update a push notification device"""
    # Check if device already exists
    result = await db.execute(
        select(PushDevice).where(PushDevice.device_token == device_token)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing device (might be switching customer)
        existing.customer_id = customer_id
        existing.device_type = device_type
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new device
    device = PushDevice(
        customer_id=customer_id,
        device_token=device_token,
        device_type=device_type,
        is_active=True
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def unregister_device(db: AsyncSession, device_token: str) -> bool:
    """Unregister a device (mark as inactive)"""
    result = await db.execute(
        select(PushDevice).where(PushDevice.device_token == device_token)
    )
    device = result.scalar_one_or_none()

    if device:
        device.is_active = False
        await db.commit()
        return True
    return False


async def get_customer_devices(db: AsyncSession, customer_id: int) -> List[PushDevice]:
    """Get all active devices for a customer"""
    result = await db.execute(
        select(PushDevice).where(
            PushDevice.customer_id == customer_id,
            PushDevice.is_active == True
        )
    )
    return result.scalars().all()


async def get_devices_for_customers(db: AsyncSession, customer_ids: List[int]) -> List[PushDevice]:
    """Get all active devices for multiple customers"""
    if not customer_ids:
        return []
    result = await db.execute(
        select(PushDevice).where(
            PushDevice.customer_id.in_(customer_ids),
            PushDevice.is_active == True
        )
    )
    return result.scalars().all()


async def deactivate_device(db: AsyncSession, device_token: str) -> None:
    """Mark a device as inactive (e.g., when FCM says token is invalid)"""
    result = await db.execute(
        select(PushDevice).where(PushDevice.device_token == device_token)
    )
    device = result.scalar_one_or_none()
    if device:
        device.is_active = False
        await db.commit()
