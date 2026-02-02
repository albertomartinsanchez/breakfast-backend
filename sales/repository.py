from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from core.repository import BaseRepository
from sales.models import Sale, SaleItem


class SaleRepository(BaseRepository[Sale]):
    """
    Repository for Sale data access operations.

    This class handles only database operations - no business logic.
    Business logic should be in the service layer.
    """

    async def get_by_id(self, id: int, user_id: int) -> Optional[Sale]:
        """Get a sale by ID with eager loading, scoped to user."""
        result = await self.db.execute(
            select(Sale)
            .where(Sale.id == id, Sale.user_id == user_id)
            .options(
                selectinload(Sale.items).selectinload(SaleItem.product),
                selectinload(Sale.items).selectinload(SaleItem.customer)
            )
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[Sale]:
        """Get all sales for a user with eager loading."""
        result = await self.db.execute(
            select(Sale)
            .where(Sale.user_id == user_id)
            .options(
                selectinload(Sale.items).selectinload(SaleItem.product),
                selectinload(Sale.items).selectinload(SaleItem.customer)
            )
        )
        return list(result.scalars().all())

    async def add(self, entity: Sale) -> Sale:
        """Add a new sale to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: Sale) -> Sale:
        """Update is implicit in SQLAlchemy - just return the entity."""
        return entity

    async def delete(self, entity: Sale) -> bool:
        """Delete a sale."""
        await self.db.delete(entity)
        return True

    async def refetch_with_relations(self, sale_id: int) -> Sale:
        """Re-fetch a sale with all relations eagerly loaded."""
        result = await self.db.execute(
            select(Sale)
            .where(Sale.id == sale_id)
            .options(
                selectinload(Sale.items).selectinload(SaleItem.product),
                selectinload(Sale.items).selectinload(SaleItem.customer)
            )
        )
        return result.scalar_one()


class SaleItemRepository(BaseRepository[SaleItem]):
    """Repository for SaleItem data access operations."""

    async def get_by_id(self, id: int, user_id: int) -> Optional[SaleItem]:
        """Get a sale item by ID."""
        result = await self.db.execute(
            select(SaleItem).where(SaleItem.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[SaleItem]:
        """Not typically used for sale items directly."""
        return []

    async def add(self, entity: SaleItem) -> SaleItem:
        """Add a new sale item to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: SaleItem) -> SaleItem:
        """Update is implicit in SQLAlchemy - just return the entity."""
        return entity

    async def delete(self, entity: SaleItem) -> bool:
        """Delete a sale item."""
        await self.db.delete(entity)
        return True
