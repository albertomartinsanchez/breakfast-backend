from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from core.repository import BaseRepository
from customers.models import Customer
from customers.models_access_token import CustomerAccessToken


class CustomerRepository(BaseRepository[Customer]):
    """
    Repository for Customer data access operations.

    This class handles only database operations - no business logic.
    Business logic should be in the service layer.
    """

    async def get_by_id(self, id: int, user_id: int) -> Optional[Customer]:
        """Get a customer by ID, scoped to user."""
        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == id, Customer.user_id == user_id)
            .options(selectinload(Customer.access_token))
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[Customer]:
        """Get all customers for a user."""
        result = await self.db.execute(
            select(Customer)
            .where(Customer.user_id == user_id)
            .options(selectinload(Customer.access_token))
        )
        return list(result.scalars().all())

    async def add(self, entity: Customer) -> Customer:
        """Add a new customer to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: Customer) -> Customer:
        """Update is implicit in SQLAlchemy - just return the entity."""
        return entity

    async def delete(self, entity: Customer) -> bool:
        """Delete a customer."""
        await self.db.delete(entity)
        return True


class CustomerAccessTokenRepository(BaseRepository[CustomerAccessToken]):
    """Repository for CustomerAccessToken data access operations."""

    async def get_by_id(self, id: int, user_id: int) -> Optional[CustomerAccessToken]:
        """Get an access token by ID."""
        result = await self.db.execute(
            select(CustomerAccessToken).where(CustomerAccessToken.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, user_id: int) -> List[CustomerAccessToken]:
        """Not typically used for access tokens."""
        return []

    async def add(self, entity: CustomerAccessToken) -> CustomerAccessToken:
        """Add a new access token to the session."""
        self.db.add(entity)
        return entity

    async def update(self, entity: CustomerAccessToken) -> CustomerAccessToken:
        """Update is implicit in SQLAlchemy - just return the entity."""
        return entity

    async def delete(self, entity: CustomerAccessToken) -> bool:
        """Delete an access token."""
        await self.db.delete(entity)
        return True
