"""Sitemap crawler using ultimate-sitemap-parser."""

import logging
from typing import List

from usp.tree import sitemap_tree_for_homepage

from .url_categorizer import URLCategorizer, CategorizedURL

logger = logging.getLogger(__name__)


class SitemapCrawler:
    """Crawl website sitemap to discover all URLs."""

    def __init__(self, base_url: str = "https://www.spca.com/en/", sitemap_url: str = "https://www.spca.com/sitemap_index.xml"):
        self.base_url = base_url
        self.sitemap_url = sitemap_url

    def discover_urls(self) -> List[str]:
        """Discover all URLs from sitemap."""
        logger.info(f"Discovering URLs from sitemap: {self.sitemap_url}")

        try:
            # Use the explicit sitemap URL instead of auto-discovery
            tree = sitemap_tree_for_homepage(self.sitemap_url)
            urls = [page.url for page in tree.all_pages()]
            logger.info(f"Discovered {len(urls)} URLs from sitemap")
            return urls
        except Exception as e:
            logger.error(f"Error discovering URLs: {e}")
            return []

    def discover_and_categorize(self) -> dict:
        """Discover URLs and categorize them."""
        urls = self.discover_urls()
        categorized = URLCategorizer.categorize_batch(urls)

        # Log summary
        for url_type, url_list in categorized.items():
            logger.info(f"  {url_type.value}: {len(url_list)} URLs")

        return categorized

    def get_scrapable_urls(self) -> List[CategorizedURL]:
        """Get only scrapable (non-ignored) URLs."""
        urls = self.discover_urls()
        return URLCategorizer.filter_scrapable(urls)

    def get_animal_urls(self) -> List[str]:
        """Get only animal page URLs."""
        from ..database.models import URLType

        categorized = self.discover_and_categorize()
        animal_urls = categorized.get(URLType.ANIMAL, [])
        return [cu.url for cu in animal_urls]

    def get_content_urls(self) -> List[str]:
        """Get general content URLs (excluding animals)."""
        from ..database.models import URLType

        categorized = self.discover_and_categorize()

        content_urls = []
        for url_type in [URLType.GENERAL, URLType.SERVICE, URLType.TIPS]:
            content_urls.extend([cu.url for cu in categorized.get(url_type, [])])

        return content_urls
