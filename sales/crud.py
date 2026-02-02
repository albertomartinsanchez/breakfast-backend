"""
DEPRECATED: This module provides backward compatibility.
New code should use SaleService from sales.service instead.

This module is kept to avoid breaking imports from other modules
(sales/router_delivery.py) that still use these functions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from sales.models import Sale
from sales.schemas import SaleCreate, SaleUpdate
from sales.service import SaleService


async def get_sales(db: AsyncSession, user_id: int) -> List[Sale]:
    """DEPRECATED: Use SaleService.get_all() instead."""
    service = SaleService(db)
    return await service.get_all(user_id)


async def get_sale_by_id(db: AsyncSession, sale_id: int, user_id: int) -> Optional[Sale]:
    """DEPRECATED: Use SaleService.get_by_id() instead."""
    service = SaleService(db)
    return await service.get_by_id(sale_id, user_id)


async def create_sale(db: AsyncSession, sale_in: SaleCreate, user_id: int) -> Sale:
    """DEPRECATED: Use SaleService.create() instead."""
    service = SaleService(db)
    return await service.create(sale_in, user_id)


async def update_sale(db: AsyncSession, sale_id: int, sale_in: SaleUpdate, user_id: int) -> Optional[Sale]:
    """DEPRECATED: Use SaleService.update() instead."""
    service = SaleService(db)
    return await service.update(sale_id, sale_in, user_id)


async def delete_sale(db: AsyncSession, sale_id: int, user_id: int) -> bool:
    """DEPRECATED: Use SaleService.delete() instead."""
    service = SaleService(db)
    return await service.delete(sale_id, user_id)
