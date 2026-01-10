"""Google Gemini File Search API client."""

import os
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from google import genai

from ..utils.config import get_settings

logger = logging.getLogger(__name__)


class FileSearchClient:
    """Client for Google Gemini File Search API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        store_name: str = "spca_knowledge_base",
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        # Configure the new genai client
        self.client = genai.Client(api_key=self.api_key)
        self.store_name = store_name
        self._files_cache: dict[str, str] = {}  # filename -> file_id
        self.file_search_store_name = None
        self._setup_file_search_store()

    def _setup_file_search_store(self) -> None:
        """Get or create file search store."""
        try:
            # List existing file search stores
            stores = list(self.client.file_search_stores.list())

            # Look for existing store
            for store in stores:
                if hasattr(store, 'display_name') and store.display_name == self.store_name:
                    self.file_search_store_name = store.name
                    logger.info(f"Using existing file search store: {self.file_search_store_name}")
                    return

            # Create new store if not found
            logger.info(f"Creating new file search store: {self.store_name}")
            store = self.client.file_search_stores.create(
                config={'display_name': self.store_name}
            )
            self.file_search_store_name = store.name
            logger.info(f"Created file search store: {self.file_search_store_name}")
        except Exception as e:
            logger.error(f"Failed to setup file search store: {e}")
            self.file_search_store_name = None

    async def upload_file(self, content: str, filename: str) -> str:
        """Upload content as a file to Google and import into file search store."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Upload to Google using new client API
            # The 'file' parameter accepts a file path as a string
            uploaded = self.client.files.upload(
                file=temp_path,
                config={'display_name': filename}
            )
            logger.info(f"Uploaded file: {filename} -> {uploaded.name}")

            # Import file into file search store if available
            if self.file_search_store_name:
                try:
                    operation = self.client.file_search_stores.import_file(
                        file_search_store_name=self.file_search_store_name,
                        file_name=uploaded.name
                    )

                    # Wait for import operation to complete (with timeout)
                    max_wait = 30  # seconds
                    wait_time = 0
                    while not operation.done and wait_time < max_wait:
                        time.sleep(2)
                        wait_time += 2
                        operation = self.client.operations.get(operation)

                    if operation.done:
                        logger.info(f"Imported file into search store: {filename}")
                    else:
                        logger.warning(f"File import timed out: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to import file into search store: {e}")

            # Cache the file ID
            self._files_cache[filename] = uploaded.name

            return uploaded.name

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google."""
        try:
            self.client.files.delete(name=file_id)
            logger.info(f"Deleted file: {file_id}")

            # Remove from cache
            self._files_cache = {
                k: v for k, v in self._files_cache.items() if v != file_id
            }

            return True
        except Exception as e:
            # Files imported into file search stores cannot be deleted
            # This is expected behavior, not an error
            if "403" in str(e) or "PERMISSION_DENIED" in str(e):
                logger.warning(f"Cannot delete file {file_id} (likely imported into file search store)")
                return False
            else:
                logger.error(f"Failed to delete file {file_id}: {e}")
                return False

    async def list_files(self) -> list[dict]:
        """List all uploaded files."""
        files = []
        files_response = self.client.files.list()
        for f in files_response:
            files.append({
                "name": f.name,
                "display_name": getattr(f, "display_name", None),
                "uri": getattr(f, "uri", None),
                "state": getattr(f, "state", {}).get("name", "UNKNOWN") if hasattr(f, "state") else "UNKNOWN",
                "size_bytes": getattr(f, "size_bytes", None),
            })
        return files

    async def get_file(self, file_id: str) -> Optional[dict]:
        """Get file information."""
        try:
            f = self.client.files.get(name=file_id)
            return {
                "name": f.name,
                "display_name": getattr(f, "display_name", None),
                "uri": getattr(f, "uri", None),
                "state": getattr(f, "state", {}).get("name", "UNKNOWN") if hasattr(f, "state") else "UNKNOWN",
            }
        except Exception as e:
            logger.error(f"Failed to get file {file_id}: {e}")
            return None

    async def upload_or_update(
        self,
        content: str,
        filename: str,
        existing_file_id: Optional[str] = None,
    ) -> str:
        """Upload new content or update existing.

        Note: Files imported into file search stores cannot be deleted,
        so we just upload a new version. Old files will remain in the store.
        """
        # Try to delete the old file (will fail for files in search stores)
        if existing_file_id:
            deleted = await self.delete_file(existing_file_id)
            if not deleted:
                logger.info(f"Uploading new version of {filename} (old version will remain)")

        # Upload new content
        return await self.upload_file(content, filename)

    def format_animal_document(self, animal: dict) -> str:
        """Format animal data as a document for RAG."""
        # Format images section
        images_section = ""
        images_url = animal.get('images_url', [])
        if images_url and isinstance(images_url, list) and len(images_url) > 0:
            images_section = "\n## Images\n"
            for idx, img_url in enumerate(images_url[:5], 1):  # Limit to first 5 images
                images_section += f"- Image {idx}: {img_url}\n"

        return f"""# {animal.get('name', 'Unknown')} - {animal.get('species', 'Animal')} for Adoption

## Basic Information
- **Name:** {animal.get('name', 'Unknown')}
- **Species:** {animal.get('species', 'Unknown')}
- **Breed:** {animal.get('breed', 'Unknown')}
- **Age:** {animal.get('age', 'Unknown')}
- **Sex:** {animal.get('sex', 'Unknown')}
- **Size:** {animal.get('size', 'Unknown')}
- **Color:** {animal.get('color', 'Unknown')}
- **Reference Number:** {animal.get('reference_number', 'Unknown')}
{images_section}
## Description
{animal.get('description', 'No description available.')}

## Adoption Status
This {animal.get('species', 'animal').lower()} is currently {animal.get('status', 'available')} for adoption at the SPCA Montreal.

## How to Adopt
To meet {animal.get('name', 'this animal')}, please visit the SPCA Montreal during opening hours.

## Profile Link
View full profile: {animal.get('source_url', 'https://www.spca.com')}
"""

    async def sync_animal(self, animal: dict) -> Optional[str]:
        """Sync a single animal to File Search."""
        ref = animal.get("reference_number")
        if not ref:
            logger.error("Animal missing reference number")
            return None

        filename = f"animal_{ref}.txt"
        content = self.format_animal_document(animal)

        existing_file_id = animal.get("google_file_id")

        try:
            file_id = await self.upload_or_update(
                content=content,
                filename=filename,
                existing_file_id=existing_file_id,
            )
            logger.info(f"Synced animal {ref} -> {file_id}")
            return file_id

        except Exception as e:
            logger.error(f"Failed to sync animal {ref}: {e}")
            return None

    async def remove_animal(self, google_file_id: str) -> bool:
        """Remove an adopted animal from File Search."""
        return await self.delete_file(google_file_id)
