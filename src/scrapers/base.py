"""Base scraper class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, Optional
import asyncio
import hashlib
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple async rate limiter."""

    def __init__(self, requests_per_second: float = 0.5, burst: int = 3):
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.tokens = burst
        self.last_update = asyncio.get_event_loop().time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request can be made."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            time_passed = now - self.last_update
            self.tokens = min(
                self.burst,
                self.tokens + time_passed * self.requests_per_second
            )
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.requests_per_second
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    )
    async def scrape(self, url: str) -> dict[str, Any]:
        """Scrape a URL with rate limiting and retries."""
        await self.rate_limiter.acquire()
        self.logger.debug(f"Scraping: {url}")

        try:
            result = await asyncio.wait_for(
                self._do_scrape(url),
                timeout=self.timeout
            )
            return result
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout scraping {url}")
            raise TimeoutError(f"Timeout scraping {url}")

    @abstractmethod
    async def _do_scrape(self, url: str) -> dict[str, Any]:
        """Actual scraping logic to be implemented by subclasses."""
        pass

    async def scrape_batch(
        self,
        urls: list[str],
        max_concurrent: int = 5,
    ) -> list[dict[str, Any]]:
        """Scrape multiple URLs with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.scrape(url)
                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    return {"url": url, "error": str(e), "success": False}

        tasks = [scrape_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove extra whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
