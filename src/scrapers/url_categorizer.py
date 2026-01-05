"""URL categorizer for routing URLs to appropriate scrapers."""

import re
from dataclasses import dataclass
from typing import List

from ..database.models import URLType


@dataclass
class CategorizedURL:
    """A URL with its categorization."""
    url: str
    url_type: URLType
    priority: int  # Lower = higher priority
    language: str = "en"  # 'en' or 'fr'


class URLCategorizer:
    """Categorize URLs based on patterns for routing to appropriate scrapers."""

    # Patterns: (regex, url_type, priority)
    PATTERNS = [
        # Animal individual pages (highest priority - change frequently)
        (r"/en/animal/[\w-]+-\d+/?", URLType.ANIMAL, 1),
        (r"/fr/animal/[\w-]+-\d+/?", URLType.ANIMAL, 1),

        # Adoption listing pages
        (r"/en/adoption/[\w-]+-for-adoption/?", URLType.ADOPTION_LIST, 2),
        (r"/fr/adoption/[\w-]+-a-adopter/?", URLType.ADOPTION_LIST, 2),

        # Service pages
        (r"/en/services/", URLType.SERVICE, 3),
        (r"/fr/services/", URLType.SERVICE, 3),

        # Tips and advice
        (r"/en/tips-and-advice/", URLType.TIPS, 4),
        (r"/fr/conseils/", URLType.TIPS, 4),

        # Ignored patterns (media, calendar, etc.)
        (r"\.(pdf|jpg|jpeg|png|gif|mp4|mp3|doc|docx|xls|xlsx)$", URLType.IGNORED, 99),
        (r"/wp-content/", URLType.IGNORED, 99),
        (r"/wp-admin/", URLType.IGNORED, 99),
        (r"/calendar/", URLType.IGNORED, 99),
        (r"/feed/", URLType.IGNORED, 99),
        (r"/cart/", URLType.IGNORED, 99),
        (r"/checkout/", URLType.IGNORED, 99),
        (r"/my-account/", URLType.IGNORED, 99),
    ]

    # Adoption listing URLs (entry points for animal discovery)
    ADOPTION_URLS = {
        "en": [
            "https://www.spca.com/en/adoption/cats-for-adoption/",
            "https://www.spca.com/en/adoption/dogs-for-adoption/",
            "https://www.spca.com/en/adoption/rabbits-for-adoption/",
            "https://www.spca.com/en/adoption/birds-for-adoption/",
            "https://www.spca.com/en/adoption/small-animals-for-adoption/",
        ],
        "fr": [
            "https://www.spca.com/fr/adoption/chats-a-adopter/",
            "https://www.spca.com/fr/adoption/chiens-a-adopter/",
            "https://www.spca.com/fr/adoption/lapins-a-adopter/",
            "https://www.spca.com/fr/adoption/oiseaux-a-adopter/",
            "https://www.spca.com/fr/adoption/petits-animaux-a-adopter/",
        ],
    }

    @classmethod
    def categorize(cls, url: str) -> CategorizedURL:
        """Categorize a single URL."""
        # Detect language
        language = "fr" if "/fr/" in url else "en"

        # Check against patterns
        for pattern, url_type, priority in cls.PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return CategorizedURL(
                    url=url,
                    url_type=url_type,
                    priority=priority,
                    language=language,
                )

        # Default to general content
        return CategorizedURL(
            url=url,
            url_type=URLType.GENERAL,
            priority=5,
            language=language,
        )

    @classmethod
    def categorize_batch(cls, urls: List[str]) -> dict[URLType, List[CategorizedURL]]:
        """Categorize multiple URLs and group by type."""
        grouped: dict[URLType, List[CategorizedURL]] = {url_type: [] for url_type in URLType}

        for url in urls:
            categorized = cls.categorize(url)
            grouped[categorized.url_type].append(categorized)

        # Sort each group by priority
        for url_type in grouped:
            grouped[url_type].sort(key=lambda x: x.priority)

        return grouped

    @classmethod
    def get_adoption_urls(cls, language: str = "en") -> List[str]:
        """Get adoption listing URLs for a language."""
        return cls.ADOPTION_URLS.get(language, cls.ADOPTION_URLS["en"])

    @classmethod
    def is_animal_page(cls, url: str) -> bool:
        """Check if URL is an individual animal page."""
        return cls.categorize(url).url_type == URLType.ANIMAL

    @classmethod
    def is_ignorable(cls, url: str) -> bool:
        """Check if URL should be ignored."""
        return cls.categorize(url).url_type == URLType.IGNORED

    @classmethod
    def extract_reference_number(cls, url: str) -> str | None:
        """Extract animal reference number from URL."""
        # URL format: /animal/name-species-REFERENCE/
        match = re.search(r"/animal/[\w-]+-(\d+)/?", url)
        if match:
            return match.group(1)
        return None

    @classmethod
    def filter_scrapable(cls, urls: List[str]) -> List[CategorizedURL]:
        """Filter and categorize only scrapable URLs."""
        categorized = cls.categorize_batch(urls)

        scrapable = []
        for url_type, urls_list in categorized.items():
            if url_type != URLType.IGNORED:
                scrapable.extend(urls_list)

        # Sort by priority
        scrapable.sort(key=lambda x: x.priority)
        return scrapable
