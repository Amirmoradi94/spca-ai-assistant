"""Factory for creating scraper instances."""

from enum import Enum
from typing import Type, Optional

from .base import BaseScraper, RateLimiter
from .animal_scraper import AnimalScraper
from .content_scraper import ContentScraper


class ScraperType(Enum):
    """Types of scrapers available."""
    ANIMAL = "animal"
    CONTENT = "content"


class ScraperFactory:
    """Factory for creating scraper instances based on type."""

    _scrapers: dict[ScraperType, Type[BaseScraper]] = {
        ScraperType.ANIMAL: AnimalScraper,
        ScraperType.CONTENT: ContentScraper,
    }

    @classmethod
    def create(
        cls,
        scraper_type: ScraperType,
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs,
    ) -> BaseScraper:
        """Create a scraper instance of the specified type."""
        if scraper_type not in cls._scrapers:
            raise ValueError(f"Unknown scraper type: {scraper_type}")

        scraper_class = cls._scrapers[scraper_type]

        if rate_limiter is None:
            rate_limiter = RateLimiter()

        return scraper_class(rate_limiter=rate_limiter, **kwargs)

    @classmethod
    def for_url(
        cls,
        url: str,
        rate_limiter: Optional[RateLimiter] = None,
        **kwargs,
    ) -> BaseScraper:
        """Automatically select scraper based on URL pattern."""
        from .url_categorizer import URLCategorizer
        from ..database.models import URLType

        categorized = URLCategorizer.categorize(url)

        if categorized.url_type == URLType.ANIMAL:
            return cls.create(ScraperType.ANIMAL, rate_limiter, **kwargs)
        else:
            return cls.create(ScraperType.CONTENT, rate_limiter, **kwargs)

    @classmethod
    def register(
        cls,
        scraper_type: ScraperType,
        scraper_class: Type[BaseScraper],
    ) -> None:
        """Register a new scraper type."""
        cls._scrapers[scraper_type] = scraper_class

    @classmethod
    def get_animal_scraper(
        cls,
        zyte_api_key: Optional[str] = None,
        use_zyte: bool = True,
    ) -> AnimalScraper:
        """Get an animal scraper instance."""
        return AnimalScraper(
            zyte_api_key=zyte_api_key,
            use_zyte=use_zyte,
        )

    @classmethod
    def get_content_scraper(
        cls,
        content_dir: str = "./content/general",
    ) -> ContentScraper:
        """Get a content scraper instance."""
        return ContentScraper(content_dir=content_dir)
