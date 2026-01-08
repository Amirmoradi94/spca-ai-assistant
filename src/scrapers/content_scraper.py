"""Content scraper using Crawl4AI for general website content."""

import os
import re
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import NoExtractionStrategy

from .base import BaseScraper, RateLimiter


class ContentScraper(BaseScraper):
    """Scraper for general content using Crawl4AI."""

    def __init__(
        self,
        content_dir: str = "./content/general",
        rate_limiter: Optional[RateLimiter] = None,
    ):
        super().__init__(rate_limiter=rate_limiter)
        self.content_dir = Path(content_dir)
        self.content_dir.mkdir(parents=True, exist_ok=True)

    async def _do_scrape(self, url: str) -> dict[str, Any]:
        """Scrape a URL using Crawl4AI."""
        try:
            async with AsyncWebCrawler(
                verbose=False,
                headless=True,
            ) as crawler:
                result = await crawler.arun(
                    url=url,
                    extraction_strategy=NoExtractionStrategy(),
                    bypass_cache=True,
                    wait_for="networkidle",  # Wait for network to be idle
                    page_timeout=30000,  # 30 seconds timeout
                    delay_before_return_html=2.0,  # Wait 2 seconds before getting content
                )

                if result.success:
                    return {
                        "url": url,
                        "html": result.html,
                        "markdown": result.markdown,
                        "title": self._extract_title(result.html),
                        "success": True,
                    }
                else:
                    return {
                        "url": url,
                        "success": False,
                        "error": result.error_message or "Unknown error",
                    }
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": str(e),
            }

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        import re
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return self.clean_text(match.group(1))
        return ""

    async def scrape_and_save(self, url: str) -> dict[str, Any]:
        """Scrape a URL and save as markdown file."""
        result = await self.scrape(url)

        if not result.get("success"):
            return result

        # Generate filename from URL
        filename = self._url_to_filename(url)
        filepath = self.content_dir / filename

        # Prepare content with metadata
        markdown_content = self._prepare_markdown(
            url=url,
            title=result.get("title", ""),
            content=result.get("markdown", ""),
        )

        # Save to file
        filepath.write_text(markdown_content, encoding="utf-8")

        # Compute hash
        content_hash = self.compute_hash(markdown_content)

        result["file_path"] = str(filepath)
        result["content_hash"] = content_hash

        self.logger.info(f"Saved content to {filepath}")
        return result

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            path = "index"

        # Replace slashes with underscores
        filename = path.replace("/", "_")

        # Remove unsafe characters
        filename = re.sub(r"[^\w\-_]", "", filename)

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        return f"{filename}.txt"

    def _prepare_markdown(self, url: str, title: str, content: str) -> str:
        """Prepare markdown content with metadata header."""
        lines = [
            f"# {title}" if title else "# Untitled",
            "",
            f"Source: {url}",
            "",
            "---",
            "",
            content,
        ]
        return "\n".join(lines)

    async def scrape_batch_and_save(
        self,
        urls: list[str],
        max_concurrent: int = 3,
    ) -> list[dict[str, Any]]:
        """Scrape multiple URLs and save each as markdown."""
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_one(url: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.scrape_and_save(url)
                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    return {"url": url, "success": False, "error": str(e)}

        tasks = [scrape_one(url) for url in urls]
        return await asyncio.gather(*tasks)

    def get_saved_files(self) -> list[Path]:
        """Get list of all saved content files."""
        return list(self.content_dir.glob("*.txt"))

    def read_content(self, filepath: Path) -> str:
        """Read content from a saved file."""
        return filepath.read_text(encoding="utf-8")
