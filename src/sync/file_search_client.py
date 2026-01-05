"""Google Gemini File Search API client."""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional

import google.generativeai as genai

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

        genai.configure(api_key=self.api_key)
        self.store_name = store_name
        self._files_cache: dict[str, str] = {}  # filename -> file_id

    async def upload_file(self, content: str, filename: str) -> str:
        """Upload content as a file to Google."""
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
            # Upload to Google
            uploaded = genai.upload_file(
                path=temp_path,
                display_name=filename,
            )
            logger.info(f"Uploaded file: {filename} -> {uploaded.name}")

            # Cache the file ID
            self._files_cache[filename] = uploaded.name

            return uploaded.name

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Google."""
        try:
            genai.delete_file(name=file_id)
            logger.info(f"Deleted file: {file_id}")

            # Remove from cache
            self._files_cache = {
                k: v for k, v in self._files_cache.items() if v != file_id
            }

            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    async def list_files(self) -> list[dict]:
        """List all uploaded files."""
        files = []
        for f in genai.list_files():
            files.append({
                "name": f.name,
                "display_name": f.display_name,
                "uri": f.uri,
                "state": f.state.name,
                "size_bytes": getattr(f, "size_bytes", None),
            })
        return files

    async def get_file(self, file_id: str) -> Optional[dict]:
        """Get file information."""
        try:
            f = genai.get_file(name=file_id)
            return {
                "name": f.name,
                "display_name": f.display_name,
                "uri": f.uri,
                "state": f.state.name,
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
        """Upload new content or update existing."""
        # If we have an existing file, delete it first
        if existing_file_id:
            await self.delete_file(existing_file_id)

        # Upload new content
        return await self.upload_file(content, filename)

    def format_animal_document(self, animal: dict) -> str:
        """Format animal data as a document for RAG."""
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
