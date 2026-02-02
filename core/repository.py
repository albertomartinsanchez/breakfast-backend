from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository defining common data access operations.

    All repositories should inherit from this class and implement
    the abstract methods for their specific entity type.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @abstractmethod
    async def get_by_id(self, id: int, user_id: int) -> Optional[T]:
        """Get a single entity by ID, scoped to user."""
        ...

    @abstractmethod
    async def get_all(self, user_id: int) -> List[T]:
        """Get all entities for a user."""
        ...

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add a new entity to the session."""
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        ...

    @abstractmethod
    async def delete(self, entity: T) -> bool:
        """Delete an entity."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db.commit()

    async def flush(self) -> None:
        """Flush pending changes without committing."""
        await self.db.flush()

    async def refresh(self, entity: T, attributes: List[str] = None) -> None:
        """Refresh an entity from the database."""
        if attributes:
            await self.db.refresh(entity, attributes)
        else:
            await self.db.refresh(entity)
