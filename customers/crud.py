"""
DEPRECATED: This module provides backward compatibility.
New code should use CustomerService from customers.service instead.

This module is kept to avoid breaking imports from other modules
(sales/router.py, sales/crud.py) that still use these functions.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from customers.models import Customer
from customers.schemas import CustomerCreate, CustomerUpdate
from customers.service import CustomerService


async def get_customers(db: AsyncSession, user_id: int) -> List[Customer]:
    """DEPRECATED: Use CustomerService.get_all() instead."""
    service = CustomerService(db)
    return await service.get_all(user_id)


async def get_customer_by_id(db: AsyncSession, customer_id: int, user_id: int) -> Optional[Customer]:
    """DEPRECATED: Use CustomerService.get_by_id() instead."""
    service = CustomerService(db)
    return await service.get_by_id(customer_id, user_id)


async def create_customer(db: AsyncSession, customer_in: CustomerCreate, user_id: int) -> Customer:
    """DEPRECATED: Use CustomerService.create() instead."""
    service = CustomerService(db)
    return await service.create(customer_in, user_id)


async def update_customer(db: AsyncSession, customer_id: int, customer_in: CustomerUpdate, user_id: int) -> Optional[Customer]:
    """DEPRECATED: Use CustomerService.update() instead."""
    service = CustomerService(db)
    return await service.update(customer_id, customer_in, user_id)


async def delete_customer(db: AsyncSession, customer_id: int, user_id: int) -> bool:
    """DEPRECATED: Use CustomerService.delete() instead."""
    service = CustomerService(db)
    return await service.delete(customer_id, user_id)
