"""Content uploader for syncing to Google File Search."""

import asyncio
import hashlib
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

    def compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def sync_all_animals(self) -> dict:
        """Sync all unsynced and modified animals to File Search."""
        logger.info("Starting animal sync")

        await emit_event(EventType.SYNC_STARTED, {"type": "animals"})

        synced = 0
        failed = 0
        updated = 0

        # Process all unsynced animals in batches
        logger.info("Phase 1: Syncing unsynced animals")
        while True:
            async with get_session() as session:
                animal_repo = AnimalRepository(session)
                sync_log_repo = SyncLogRepository(session)

                # Get next batch of unsynced animals
                unsynced = await animal_repo.get_unsynced(limit=self.batch_size)

                if not unsynced:
                    logger.info("No more unsynced animals found")
                    break

                logger.info(f"Processing batch of {len(unsynced)} unsynced animals")

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
                            "images_url": animal.images_url if animal.images_url else [],
                            "google_file_id": animal.google_file_id,
                        }

                        file_id = await self.client.sync_animal(animal_data)

                        if file_id:
                            await animal_repo.mark_synced(animal.id, file_id)
                            await sync_log_repo.log_sync(
                                entity_type="animal",
                                entity_id=animal.reference_number,
                                action="create",
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
                logger.info(f"Batch complete: {synced} total synced, {failed} total failed")

        # Process modified synced animals in batches
        logger.info("Phase 2: Syncing modified animals")
        while True:
            async with get_session() as session:
                animal_repo = AnimalRepository(session)
                sync_log_repo = SyncLogRepository(session)

                # Get next batch of modified synced animals
                modified = await animal_repo.get_modified_synced(limit=self.batch_size)

                if not modified:
                    logger.info("No modified synced animals found")
                    break

                logger.info(f"Processing batch of {len(modified)} modified animals")

                for animal in modified:
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
                            "images_url": animal.images_url if animal.images_url else [],
                            "google_file_id": animal.google_file_id,  # Pass existing ID for update
                        }

                        # This will delete old file and upload new one
                        file_id = await self.client.sync_animal(animal_data)

                        if file_id:
                            await animal_repo.mark_synced(animal.id, file_id)
                            await sync_log_repo.log_sync(
                                entity_type="animal",
                                entity_id=animal.reference_number,
                                action="update",
                                google_file_id=file_id,
                            )
                            updated += 1
                            synced += 1
                        else:
                            failed += 1
                            await sync_log_repo.log_sync(
                                entity_type="animal",
                                entity_id=animal.reference_number,
                                action="update",
                                status="failed",
                                error_message="Upload returned None",
                            )

                    except Exception as e:
                        logger.error(f"Failed to update animal {animal.reference_number}: {e}")
                        failed += 1
                        await sync_log_repo.log_sync(
                            entity_type="animal",
                            entity_id=animal.reference_number,
                            action="update",
                            status="failed",
                            error_message=str(e),
                        )

                await session.commit()
                logger.info(f"Batch complete: {synced} total synced ({updated} updates), {failed} total failed")

        await emit_event(
            EventType.SYNC_COMPLETED,
            {"type": "animals", "synced": synced, "updated": updated, "failed": failed},
        )

        logger.info(f"Animal sync complete: {synced} total synced ({updated} updates), {failed} failed")
        return {"synced": synced, "updated": updated, "failed": failed}

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
        """Sync general content files to File Search with deduplication."""
        logger.info("Starting content file sync with deduplication")

        await emit_event(EventType.SYNC_STARTED, {"type": "content"})

        synced = 0
        failed = 0
        skipped = 0

        # Get all content files
        content_files = list(self.content_dir.glob("*.txt"))
        total_files = len(content_files)
        logger.info(f"Found {total_files} content files")

        # Process files in batches
        for batch_start in range(0, total_files, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_files)
            batch = content_files[batch_start:batch_end]

            logger.info(f"Processing content batch {batch_start + 1}-{batch_end} of {total_files}")

            async with get_session() as session:
                sync_log_repo = SyncLogRepository(session)

                for filepath in batch:
                    try:
                        content = filepath.read_text(encoding="utf-8")
                        filename = filepath.name
                        content_hash = self.compute_hash(content)

                        # Check if file was already synced
                        existing_syncs = await sync_log_repo.get_by_entity("content", filename)

                        if existing_syncs:
                            # File was synced before - skip to avoid duplicates
                            last_sync = existing_syncs[0]  # Most recent sync

                            if last_sync.status == "success":
                                # Check if content changed
                                if last_sync.content_hash == content_hash:
                                    logger.info(f"Skipping {filename} - already synced, no changes")
                                else:
                                    logger.info(f"Skipping {filename} - already synced (content changed but cannot update)")
                                skipped += 1
                                continue  # Skip - file already exists
                            else:
                                # Previous sync failed, retry upload
                                logger.info(f"Retrying {filename} - previous sync failed")
                                file_id = await self.client.upload_file(content, filename)
                                action = "create"

                                if file_id:
                                    await sync_log_repo.log_sync(
                                        entity_type="content",
                                        entity_id=filename,
                                        action=action,
                                        google_file_id=file_id,
                                        content_hash=content_hash,
                                    )
                                    synced += 1
                                else:
                                    failed += 1
                        else:
                            # New file - upload
                            logger.info(f"New file {filename}, uploading")
                            file_id = await self.client.upload_file(content, filename)
                            action = "create"

                            if file_id:
                                await sync_log_repo.log_sync(
                                    entity_type="content",
                                    entity_id=filename,
                                    action=action,
                                    google_file_id=file_id,
                                    content_hash=content_hash,
                                )
                                synced += 1
                            else:
                                failed += 1

                    except Exception as e:
                        logger.error(f"Failed to sync content file {filepath}: {e}")
                        failed += 1

                await session.commit()
                logger.info(
                    f"Batch complete: {synced} total synced, "
                    f"{skipped} skipped, {failed} failed"
                )

        await emit_event(
            EventType.SYNC_COMPLETED,
            {"type": "content", "synced": synced, "skipped": skipped, "failed": failed},
        )

        logger.info(
            f"Content sync complete: {synced} synced, "
            f"{skipped} skipped, {failed} failed"
        )
        return {"synced": synced, "skipped": skipped, "failed": failed}

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
