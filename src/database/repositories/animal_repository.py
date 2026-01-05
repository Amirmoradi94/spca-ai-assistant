"""Repository for Animal data access."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Animal, AnimalStatus


class AnimalRepository(BaseRepository[Animal]):
    """Repository for Animal CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> Optional[Animal]:
        """Get animal by ID."""
        result = await self.session.execute(
            select(Animal).where(Animal.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference_number: str) -> Optional[Animal]:
        """Get animal by reference number."""
        result = await self.session.execute(
            select(Animal).where(Animal.reference_number == reference_number)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Animal]:
        """Get all animals with pagination."""
        result = await self.session.execute(
            select(Animal)
            .order_by(Animal.first_seen_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_species(self, species: str, limit: int = 100) -> List[Animal]:
        """Get animals by species."""
        result = await self.session.execute(
            select(Animal)
            .where(Animal.species == species)
            .where(Animal.status == AnimalStatus.AVAILABLE)
            .order_by(Animal.first_seen_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_available(self, limit: int = 100, offset: int = 0) -> List[Animal]:
        """Get all available animals."""
        result = await self.session.execute(
            select(Animal)
            .where(Animal.status == AnimalStatus.AVAILABLE)
            .order_by(Animal.first_seen_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_unsynced(self, limit: int = 100) -> List[Animal]:
        """Get animals not yet synced to Google File Search."""
        result = await self.session.execute(
            select(Animal)
            .where(Animal.synced_to_google == False)  # noqa: E712
            .where(Animal.status == AnimalStatus.AVAILABLE)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: AnimalStatus, limit: int = 100) -> List[Animal]:
        """Get animals by status."""
        result = await self.session.execute(
            select(Animal)
            .where(Animal.status == status)
            .order_by(Animal.first_seen_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, animal: Animal) -> Animal:
        """Create a new animal."""
        self.session.add(animal)
        await self.session.flush()
        await self.session.refresh(animal)
        return animal

    async def update(self, animal: Animal) -> Animal:
        """Update an existing animal."""
        await self.session.merge(animal)
        await self.session.flush()
        return animal

    async def delete(self, id: int) -> bool:
        """Delete an animal by ID."""
        result = await self.session.execute(
            delete(Animal).where(Animal.id == id)
        )
        return result.rowcount > 0

    async def upsert(self, animal_data: dict) -> Animal:
        """Insert or update animal based on reference_number."""
        reference_number = animal_data.get("reference_number")
        if not reference_number:
            raise ValueError("reference_number is required for upsert")

        existing = await self.get_by_reference(reference_number)

        if existing:
            # Update existing record
            for key, value in animal_data.items():
                if key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            existing.last_scraped_at = datetime.utcnow()
            await self.session.flush()
            return existing
        else:
            # Create new record
            animal = Animal(**animal_data)
            animal.last_scraped_at = datetime.utcnow()
            self.session.add(animal)
            await self.session.flush()
            await self.session.refresh(animal)
            return animal

    async def mark_synced(
        self, animal_id: int, google_file_id: str
    ) -> None:
        """Mark an animal as synced to Google File Search."""
        await self.session.execute(
            update(Animal)
            .where(Animal.id == animal_id)
            .values(
                synced_to_google=True,
                google_file_id=google_file_id,
                last_synced_at=datetime.utcnow(),
            )
        )

    async def mark_adopted(self, reference_number: str) -> Optional[Animal]:
        """Mark an animal as adopted."""
        animal = await self.get_by_reference(reference_number)
        if animal:
            animal.status = AnimalStatus.ADOPTED
            animal.last_modified_at = datetime.utcnow()
            await self.session.flush()
        return animal

    async def get_all_reference_numbers(self) -> set[str]:
        """Get all reference numbers currently in database."""
        result = await self.session.execute(
            select(Animal.reference_number)
        )
        return {row[0] for row in result.all()}

    async def count_by_species(self) -> dict[str, int]:
        """Get count of available animals by species."""
        result = await self.session.execute(
            select(Animal.species, func.count(Animal.id))
            .where(Animal.status == AnimalStatus.AVAILABLE)
            .group_by(Animal.species)
        )
        return {species: count for species, count in result.all()}

    async def search(
        self,
        species: Optional[str] = None,
        sex: Optional[str] = None,
        size: Optional[str] = None,
        limit: int = 50,
    ) -> List[Animal]:
        """Search animals with filters."""
        query = select(Animal).where(Animal.status == AnimalStatus.AVAILABLE)

        if species:
            query = query.where(Animal.species == species)
        if sex:
            query = query.where(Animal.sex == sex)
        if size:
            query = query.where(Animal.size == size)

        query = query.order_by(Animal.first_seen_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
