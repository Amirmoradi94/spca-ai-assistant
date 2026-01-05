"""Content uploader for syncing to Google File Search."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from ..database.session import get_session
from ..database.repositories.animal_repository import AnimalRepository
from ..database.repositories.scrape_repository import SyncLogRepository
from ..database.models import AnimalStatus
from ..pipeline.events import EventType, emit_event
from .file_search_client import FileSearchClient

logger = logging.getLogger(__name__)


class ContentUploader:
    """Uploads content to Google File Search."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        content_dir: str = "./content/general",
        batch_size: int = 50,
    ):
        self.client = FileSearchClient(api_key=api_key)
        self.content_dir = Path(content_dir)
        self.batch_size = batch_size

    async def sync_all_animals(self) -> dict:
        """Sync all unsynced animals to File Search."""
        logger.info("Starting animal sync")

        await emit_event(EventType.SYNC_STARTED, {"type": "animals"})

        synced = 0
        failed = 0

        async with get_session() as session:
            animal_repo = AnimalRepository(session)
            sync_log_repo = SyncLogRepository(session)

            # Get unsynced animals
            unsynced = await animal_repo.get_unsynced(limit=self.batch_size)
            logger.info(f"Found {len(unsynced)} unsynced animals")

            for animal in unsynced:
                try:
                    # Convert to dict
                    animal_data = {
                        "reference_number": animal.reference_number,
                        "name": animal.name,
                        "species": animal.species,
                        "breed": animal.breed,
                        "age": animal.age,
                        "sex": animal.sex,
                        "size": animal.size,
                        "color": animal.color,
                        "description": animal.description,
                        "status": animal.status.value if animal.status else "available",
                        "source_url": animal.source_url,
                        "google_file_id": animal.google_file_id,
                    }

                    file_id = await self.client.sync_animal(animal_data)

                    if file_id:
                        await animal_repo.mark_synced(animal.id, file_id)
                        await sync_log_repo.log_sync(
                            entity_type="animal",
                            entity_id=animal.reference_number,
                            action="create" if not animal.google_file_id else "update",
                            google_file_id=file_id,
                        )
                        synced += 1
                    else:
                        failed += 1
                        await sync_log_repo.log_sync(
                            entity_type="animal",
                            entity_id=animal.reference_number,
                            action="create",
                            status="failed",
                            error_message="Upload returned None",
                        )

                except Exception as e:
                    logger.error(f"Failed to sync animal {animal.reference_number}: {e}")
                    failed += 1
                    await sync_log_repo.log_sync(
                        entity_type="animal",
                        entity_id=animal.reference_number,
                        action="create",
                        status="failed",
                        error_message=str(e),
                    )

            await session.commit()

        await emit_event(
            EventType.SYNC_COMPLETED,
            {"type": "animals", "synced": synced, "failed": failed},
        )

        logger.info(f"Animal sync complete: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed}

    async def sync_adopted_animals(self) -> dict:
        """Remove adopted animals from File Search."""
        logger.info("Syncing adopted animals (removal)")

        removed = 0
        failed = 0

        async with get_session() as session:
            animal_repo = AnimalRepository(session)
            sync_log_repo = SyncLogRepository(session)

            # Get adopted animals that are still synced
            adopted = await animal_repo.get_by_status(AnimalStatus.ADOPTED, limit=100)

            for animal in adopted:
                if animal.google_file_id:
                    try:
                        success = await self.client.remove_animal(animal.google_file_id)

                        if success:
                            # Clear the sync status
                            animal.synced_to_google = False
                            animal.google_file_id = None
                            await sync_log_repo.log_sync(
                                entity_type="animal",
                                entity_id=animal.reference_number,
                                action="delete",
                            )
                            removed += 1
                        else:
                            failed += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to remove adopted animal {animal.reference_number}: {e}"
                        )
                        failed += 1

            await session.commit()

        logger.info(f"Adopted animals sync: {removed} removed, {failed} failed")
        return {"removed": removed, "failed": failed}

    async def sync_content_files(self) -> dict:
        """Sync general content files to File Search."""
        logger.info("Starting content file sync")

        await emit_event(EventType.SYNC_STARTED, {"type": "content"})

        synced = 0
        failed = 0

        # Get all content files
        content_files = list(self.content_dir.glob("*.txt"))
        logger.info(f"Found {len(content_files)} content files")

        async with get_session() as session:
            sync_log_repo = SyncLogRepository(session)

            for filepath in content_files[:self.batch_size]:
                try:
                    content = filepath.read_text(encoding="utf-8")
                    filename = filepath.name

                    file_id = await self.client.upload_file(content, filename)

                    if file_id:
                        await sync_log_repo.log_sync(
                            entity_type="content",
                            entity_id=filename,
                            action="create",
                            google_file_id=file_id,
                        )
                        synced += 1
                    else:
                        failed += 1

                except Exception as e:
                    logger.error(f"Failed to sync content file {filepath}: {e}")
                    failed += 1

            await session.commit()

        await emit_event(
            EventType.SYNC_COMPLETED,
            {"type": "content", "synced": synced, "failed": failed},
        )

        logger.info(f"Content sync complete: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed}

    async def full_sync(self) -> dict:
        """Run a full sync of all content."""
        logger.info("Starting full sync")

        animals_result = await self.sync_all_animals()
        adopted_result = await self.sync_adopted_animals()
        content_result = await self.sync_content_files()

        return {
            "animals": animals_result,
            "adopted": adopted_result,
            "content": content_result,
        }
