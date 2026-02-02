"""
DEPRECATED: This module provides backward compatibility.
New code should use ProductService from products.service instead.

This module is kept to avoid breaking imports from other modules
(sales/crud.py) that still use these functions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from products.models import Product
from products.schemas import ProductCreate, ProductUpdate
from products.service import ProductService


async def get_products(db: AsyncSession, user_id: int) -> List[Product]:
    """DEPRECATED: Use ProductService.get_all() instead."""
    service = ProductService(db)
    return await service.get_all(user_id)


async def get_product_by_id(db: AsyncSession, product_id: int, user_id: int) -> Optional[Product]:
    """DEPRECATED: Use ProductService.get_by_id() instead."""
    service = ProductService(db)
    return await service.get_by_id(product_id, user_id)


async def create_product(db: AsyncSession, product_in: ProductCreate, user_id: int) -> Product:
    """DEPRECATED: Use ProductService.create() instead."""
    service = ProductService(db)
    return await service.create(product_in, user_id)


async def update_product(db: AsyncSession, product_id: int, product_in: ProductUpdate, user_id: int) -> Optional[Product]:
    """DEPRECATED: Use ProductService.update() instead."""
    service = ProductService(db)
    return await service.update(product_id, product_in, user_id)


async def delete_product(db: AsyncSession, product_id: int, user_id: int) -> bool:
    """DEPRECATED: Use ProductService.delete() instead."""
    service = ProductService(db)
    return await service.delete(product_id, user_id)
