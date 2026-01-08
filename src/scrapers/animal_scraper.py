"""Animal scraper using Zyte API and BeautifulSoup."""

import os
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, RateLimiter


class AnimalScraper(BaseScraper):
    """Scraper for animal pages using Zyte API + BeautifulSoup."""

    # Selectors for pet listing page
    PET_CARD_CONTAINER = "div.pet--row"
    PET_CARD_SELECTOR = "div.single--card.pet--card"
    PET_LINK_SELECTOR = "a.card--link"
    PET_NAME_SELECTOR = "h5.card--title"
    PET_INFO_SELECTOR = "div.pet--infos"

    # Selectors for individual pet page
    PET_PAGE_CONTAINER = "div.single-pet"
    PET_IMAGES_CONTAINER = "div.pet--images"
    PET_INFO_COLUMN = "div.pet-single-column"

    def __init__(
        self,
        zyte_api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        use_zyte: bool = True,
    ):
        super().__init__(rate_limiter=rate_limiter)
        self.zyte_api_key = zyte_api_key or os.getenv("ZYTE_API_KEY")
        self.use_zyte = use_zyte and bool(self.zyte_api_key)
        self.base_url = "https://www.spca.com"

    async def _do_scrape(self, url: str) -> dict[str, Any]:
        """Scrape a URL and return raw HTML."""
        html = await self._fetch_html(url)
        return {"url": url, "html": html, "success": True}

    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from URL."""
        if self.use_zyte:
            return await self._fetch_with_zyte(url)
        else:
            return await self._fetch_with_httpx(url)

    async def _fetch_with_zyte(self, url: str) -> str:
        """Fetch using Zyte API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.zyte.com/v1/extract",
                auth=(self.zyte_api_key, ""),
                json={
                    "url": url,
                    "httpResponseBody": True,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Decode base64 response body
            import base64
            html_bytes = base64.b64decode(data.get("httpResponseBody", ""))
            return html_bytes.decode("utf-8")

    async def _fetch_with_httpx(self, url: str) -> str:
        """Fetch using httpx (for development/testing)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SPCABot/1.0)",
                },
                timeout=30.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    async def scrape_listing_page(self, url: str) -> list[dict[str, Any]]:
        """Scrape an adoption listing page to get all pet URLs."""
        result = await self.scrape(url)
        if not result.get("success"):
            return []

        html = result.get("html", "")
        soup = BeautifulSoup(html, "lxml")

        pets = []
        pet_cards = soup.select(self.PET_CARD_SELECTOR)

        for card in pet_cards:
            link = card.select_one(self.PET_LINK_SELECTOR)
            if not link:
                continue

            pet_url = link.get("href", "")
            if not pet_url.startswith("http"):
                pet_url = urljoin(self.base_url, pet_url)

            name_elem = card.select_one(self.PET_NAME_SELECTOR)
            info_elem = card.select_one(self.PET_INFO_SELECTOR)

            # Parse quick info: "Dog ● Young ● Male ● L"
            quick_info = {}
            if info_elem:
                info_text = info_elem.get_text(strip=True)
                parts = [p.strip() for p in info_text.split("●")]
                if len(parts) >= 1:
                    quick_info["species"] = parts[0]
                if len(parts) >= 2:
                    quick_info["age_category"] = parts[1]
                if len(parts) >= 3:
                    quick_info["sex"] = parts[2]
                if len(parts) >= 4:
                    quick_info["size"] = parts[3]

            # Get thumbnail
            img = card.select_one("div.card--image img")
            thumbnail = img.get("src", "") if img else ""

            pets.append({
                "url": pet_url,
                "name": name_elem.get_text(strip=True) if name_elem else "",
                "thumbnail": thumbnail,
                **quick_info,
            })

        self.logger.info(f"Found {len(pets)} pets on {url}")
        return pets

    async def scrape_listing_with_pagination(self, base_url: str, max_pages: int = 50) -> list[dict[str, Any]]:
        """
        Scrape all pages of an adoption listing until no more pets are found.

        Args:
            base_url: Base URL like https://www.spca.com/en/adoption/cats-for-adoption/
            max_pages: Maximum number of pages to scrape (safety limit)

        Returns:
            List of all pets found across all pages
        """
        all_pets = []
        page = 1

        # Remove trailing slash for consistent URL building
        base_url = base_url.rstrip('/')

        while page <= max_pages:
            # Build page URL
            if page == 1:
                page_url = base_url + '/'
            else:
                page_url = f"{base_url}/page/{page}/"

            self.logger.info(f"Scraping page {page}: {page_url}")

            # Scrape this page
            pets = await self.scrape_listing_page(page_url)

            # If no pets found, we've reached the end
            if not pets:
                self.logger.info(f"No pets found on page {page}, stopping pagination")
                break

            all_pets.extend(pets)
            self.logger.info(f"Page {page}: Found {len(pets)} pets (total so far: {len(all_pets)})")

            page += 1

        self.logger.info(f"Pagination complete. Total pets found: {len(all_pets)} across {page - 1} pages")
        return all_pets

    async def scrape_animal_page(self, url: str) -> dict[str, Any]:
        """Scrape an individual animal page for full details."""
        result = await self.scrape(url)
        if not result.get("success"):
            return {"url": url, "success": False, "error": result.get("error")}

        html = result.get("html", "")
        return self.parse_animal_page(html, url)

    def parse_animal_page(self, html: str, url: str) -> dict[str, Any]:
        """Parse animal page HTML and extract all fields."""
        soup = BeautifulSoup(html, "lxml")

        # Find the main container
        container = soup.select_one(self.PET_PAGE_CONTAINER)
        if not container:
            return {"url": url, "success": False, "error": "Pet container not found"}

        animal_data = {
            "source_url": url,
            "success": True,
        }

        # Extract name from h2
        name_elem = container.select_one("h2")
        if name_elem:
            animal_data["name"] = self.clean_text(name_elem.get_text())

        # Extract description
        desc_header = container.find("h5", string=re.compile(r"Description", re.I))
        if desc_header:
            desc_elem = desc_header.find_next_sibling("p")
            if desc_elem:
                animal_data["description"] = self.clean_text(desc_elem.get_text())

        # Extract table fields
        table = container.select_one("table")
        if table:
            rows = table.select("tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) >= 2:
                    field_name = self.clean_text(cells[0].get_text()).lower()
                    field_value = self.clean_text(cells[1].get_text())

                    # Map field names to model fields
                    field_mapping = {
                        "reference number": "reference_number",
                        "species": "species",
                        "age": "age",
                        "sex": "sex",
                        "breed": "breed",
                        "size": "size",
                        "color": "color",
                        "declawed": "declawed",
                        "weight": "weight",
                    }

                    model_field = field_mapping.get(field_name)
                    if model_field:
                        if model_field == "declawed":
                            animal_data[model_field] = field_value.lower() == "yes"
                        else:
                            animal_data[model_field] = field_value

        # Extract images
        images = []
        images_container = container.select_one(self.PET_IMAGES_CONTAINER)
        if images_container:
            # Main image
            main_img = images_container.select_one("img.rollover-parent")
            if main_img and main_img.get("src"):
                images.append(main_img["src"])

            # Thumbnail images
            thumbnails = images_container.select("div.pet--thumbnail img")
            for thumb in thumbnails:
                src = thumb.get("src")
                if src and src not in images:
                    images.append(src)

        animal_data["images_url"] = images

        # Compute content hash for change detection
        content_for_hash = f"{animal_data.get('name', '')}{animal_data.get('description', '')}{animal_data.get('status', '')}"
        animal_data["content_hash"] = self.compute_hash(content_for_hash)

        return animal_data

    async def scrape_all_animals(self, language: str = "en") -> list[dict[str, Any]]:
        """Scrape all animals from all adoption listing pages."""
        from .url_categorizer import URLCategorizer

        listing_urls = URLCategorizer.get_adoption_urls(language)
        all_animals = []

        for listing_url in listing_urls:
            self.logger.info(f"Scraping listing: {listing_url}")
            pet_cards = await self.scrape_listing_page(listing_url)

            for pet_card in pet_cards:
                pet_url = pet_card.get("url")
                if pet_url:
                    self.logger.info(f"Scraping animal: {pet_url}")
                    animal_data = await self.scrape_animal_page(pet_url)
                    if animal_data.get("success"):
                        all_animals.append(animal_data)

        self.logger.info(f"Total animals scraped: {len(all_animals)}")
        return all_animals
