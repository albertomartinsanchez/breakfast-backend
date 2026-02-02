from sqlalchemy import select
from typing import List, Optional

from core.repository import BaseRepository
from products.models import Product


class ProductRepository(BaseRepository[Product]):
    """
    Repository for Product data access operations.

    This class handles only database operations - no business logic.
    Business logic should be in the service layer.
    """

    async def get_by_id(self, id: int, user_id: int) -> Optional[Product]:
        """Get a product by ID, scoped to user."""
        result = await self.db.execute(
            select(Product).where(Product.id == id, Product.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[Product]:
        """Get all products for a user."""
        result = await self.db.execute(
            select(Product).where(Product.user_id == user_id)
        )
        return list(result.scalars().all())

    async def add(self, entity: Product) -> Product:
        """Add a new product to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: Product) -> Product:
        """Update is implicit in SQLAlchemy - just return the entity."""
        return entity

    async def delete(self, entity: Product) -> bool:
        """Delete a product."""
        await self.db.delete(entity)
        return True
