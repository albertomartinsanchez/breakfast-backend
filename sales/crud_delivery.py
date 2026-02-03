"""
Backward-compatible wrapper for delivery operations.

This module provides the old function signatures that delegate to
DeliveryService for any code that still imports from crud_delivery.

New code should import from delivery_service directly.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict

from sales.delivery_service import DeliveryService


async def start_delivery(db: AsyncSession, sale_id: int, user_id: int) -> bool:
    """Start delivery process."""
    service = DeliveryService(db)
    return await service.start_delivery(sale_id, user_id)


async def get_delivery_route(db: AsyncSession, sale_id: int, user_id: int) -> List[Dict]:
    """Get all delivery steps for a sale with customer and item details."""
    service = DeliveryService(db)
    return await service.get_delivery_route(sale_id, user_id)


async def update_delivery_route(
    db: AsyncSession,
    sale_id: int,
    route: List[Dict],
    user_id: int
) -> bool:
    """Update sequence order or create steps if none exist."""
    service = DeliveryService(db)
    return await service.update_delivery_route(sale_id, route, user_id)


async def set_next_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    user_id: int
) -> bool:
    """Set a customer as the next delivery."""
    service = DeliveryService(db)
    return await service.set_next_delivery(sale_id, customer_id, user_id)


async def complete_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    amount_collected: float,
    user_id: int
) -> Dict:
    """Mark a delivery step as completed and apply customer credit."""
    service = DeliveryService(db)
    return await service.complete_delivery(sale_id, customer_id, amount_collected, user_id)


async def skip_delivery(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    reason: str,
    user_id: int
) -> bool:
    """Skip a delivery step."""
    service = DeliveryService(db)
    return await service.skip_delivery(sale_id, customer_id, reason, user_id)


async def reset_delivery_to_pending(
    db: AsyncSession,
    sale_id: int,
    customer_id: int,
    user_id: int
) -> bool:
    """Reset a delivery step back to pending."""
    service = DeliveryService(db)
    return await service.reset_delivery_to_pending(sale_id, customer_id, user_id)


async def get_delivery_progress(db: AsyncSession, sale_id: int, user_id: int) -> Dict:
    """Get delivery progress statistics."""
    service = DeliveryService(db)
    return await service.get_delivery_progress(sale_id, user_id)
