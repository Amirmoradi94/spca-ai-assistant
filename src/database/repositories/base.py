"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository defining the interface for data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all entities with pagination."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete an entity by ID."""
        pass

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.session.commit()

    async def flush(self) -> None:
        """Flush pending changes."""
        await self.session.flush()

    async def refresh(self, entity: T) -> None:
        """Refresh entity from database."""
        await self.session.refresh(entity)
