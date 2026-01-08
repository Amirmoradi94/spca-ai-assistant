"""Pipeline orchestrator for coordinating scraping operations."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..database.session import get_session
from ..database.repositories.animal_repository import AnimalRepository
from ..database.repositories.scrape_repository import (
    ScrapeJobRepository,
    ScrapedURLRepository,
)
from ..database.models import Animal, JobType, URLType
from ..scrapers.animal_scraper import AnimalScraper
from ..scrapers.content_scraper import ContentScraper
from ..scrapers.sitemap_crawler import SitemapCrawler
from ..scrapers.url_categorizer import URLCategorizer
from .events import EventType, emit_event

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates the scraping pipeline."""

    def __init__(
        self,
        zyte_api_key: Optional[str] = None,
        use_zyte: bool = True,
        content_dir: str = "./content/general",
    ):
        self.animal_scraper = AnimalScraper(
            zyte_api_key=zyte_api_key,
            use_zyte=use_zyte,
        )
        self.content_scraper = ContentScraper(content_dir=content_dir)
        self.sitemap_crawler = SitemapCrawler()

    async def run_full_scrape(self) -> dict:
        """Run a complete scrape: sitemap + animals + content."""
        logger.info("Starting full scrape")

        async with get_session() as session:
            job_repo = ScrapeJobRepository(session)
            job = await job_repo.start_job(JobType.FULL)

            await emit_event(EventType.SCRAPE_STARTED, {"job_id": job.id, "type": "full"})

            try:
                # Discover URLs from sitemap
                categorized = self.sitemap_crawler.discover_and_categorize()

                urls_discovered = sum(len(urls) for urls in categorized.values())

                # Scrape animals
                animal_results = await self._scrape_animals(session)

                # Scrape content
                content_results = await self._scrape_content(session, categorized)

                urls_scraped = animal_results["scraped"] + content_results["scraped"]
                urls_failed = animal_results["failed"] + content_results["failed"]

                await job_repo.complete_job(
                    job.id,
                    urls_discovered=urls_discovered,
                    urls_scraped=urls_scraped,
                    urls_failed=urls_failed,
                )

                await emit_event(
                    EventType.SCRAPE_COMPLETED,
                    {
                        "job_id": job.id,
                        "urls_discovered": urls_discovered,
                        "urls_scraped": urls_scraped,
                        "urls_failed": urls_failed,
                    },
                )

                # Trigger sync
                await emit_event(EventType.SYNC_REQUIRED, {"job_id": job.id})

                return {
                    "job_id": job.id,
                    "urls_discovered": urls_discovered,
                    "urls_scraped": urls_scraped,
                    "urls_failed": urls_failed,
                    "status": "completed",
                }

            except Exception as e:
                logger.error(f"Full scrape failed: {e}")
                await job_repo.fail_job(job.id, str(e))
                await emit_event(
                    EventType.SCRAPE_FAILED, {"job_id": job.id, "error": str(e)}
                )
                raise

    async def run_animal_scrape(self) -> dict:
        """Scrape only animal pages."""
        logger.info("Starting animal scrape")

        async with get_session() as session:
            job_repo = ScrapeJobRepository(session)
            job = await job_repo.start_job(JobType.ANIMALS_ONLY)

            await emit_event(
                EventType.SCRAPE_STARTED, {"job_id": job.id, "type": "animals"}
            )

            try:
                results = await self._scrape_animals(session)

                await job_repo.complete_job(
                    job.id,
                    urls_discovered=results["discovered"],
                    urls_scraped=results["scraped"],
                    urls_failed=results["failed"],
                )

                await emit_event(
                    EventType.SCRAPE_COMPLETED,
                    {"job_id": job.id, **results},
                )

                await emit_event(EventType.SYNC_REQUIRED, {"job_id": job.id})

                return {"job_id": job.id, "status": "completed", **results}

            except Exception as e:
                logger.error(f"Animal scrape failed: {e}")
                await job_repo.fail_job(job.id, str(e))
                await emit_event(
                    EventType.SCRAPE_FAILED, {"job_id": job.id, "error": str(e)}
                )
                raise

    async def run_content_scrape(self) -> dict:
        """Scrape only general content pages."""
        logger.info("Starting content scrape")

        async with get_session() as session:
            job_repo = ScrapeJobRepository(session)
            job = await job_repo.start_job(JobType.CONTENT_ONLY)

            await emit_event(
                EventType.SCRAPE_STARTED, {"job_id": job.id, "type": "content"}
            )

            try:
                # Get URLs from sitemap
                categorized = self.sitemap_crawler.discover_and_categorize()
                results = await self._scrape_content(session, categorized)

                await job_repo.complete_job(
                    job.id,
                    urls_discovered=results["discovered"],
                    urls_scraped=results["scraped"],
                    urls_failed=results["failed"],
                )

                await emit_event(
                    EventType.SCRAPE_COMPLETED,
                    {"job_id": job.id, **results},
                )

                await emit_event(EventType.SYNC_REQUIRED, {"job_id": job.id})

                return {"job_id": job.id, "status": "completed", **results}

            except Exception as e:
                logger.error(f"Content scrape failed: {e}")
                await job_repo.fail_job(job.id, str(e))
                await emit_event(
                    EventType.SCRAPE_FAILED, {"job_id": job.id, "error": str(e)}
                )
                raise

    async def _scrape_animals(self, session) -> dict:
        """Scrape all animals from adoption pages."""
        animal_repo = AnimalRepository(session)
        url_repo = ScrapedURLRepository(session)

        discovered = 0
        scraped = 0
        failed = 0

        # Get current animals to detect adopted ones
        existing_refs = await animal_repo.get_all_reference_numbers()
        found_refs = set()

        # Scrape from all adoption listing pages
        for language in ["en"]:  # Start with English only
            listing_urls = URLCategorizer.get_adoption_urls(language)

            for listing_url in listing_urls:
                logger.info(f"Scraping listing with pagination: {listing_url}")

                try:
                    # Scrape all pages until no more pets found
                    pet_cards = await self.animal_scraper.scrape_listing_with_pagination(listing_url)
                    discovered += len(pet_cards)

                    for pet_card in pet_cards:
                        pet_url = pet_card.get("url")
                        if not pet_url:
                            continue

                        try:
                            # Track URL
                            await url_repo.upsert(pet_url, URLType.ANIMAL)

                            # Scrape individual page
                            animal_data = await self.animal_scraper.scrape_animal_page(
                                pet_url
                            )

                            if animal_data.get("success"):
                                # Save to database (remove non-model fields)
                                db_data = {k: v for k, v in animal_data.items() if k not in ('success', 'error')}

                                try:
                                    await animal_repo.upsert(db_data)
                                    await session.commit()  # Commit after each animal
                                    scraped += 1

                                    ref = animal_data.get("reference_number")
                                    if ref:
                                        found_refs.add(ref)

                                    await url_repo.mark_success(
                                        pet_url,
                                        animal_data.get("content_hash", ""),
                                    )

                                    await emit_event(
                                        EventType.ANIMAL_UPDATED,
                                        {"reference": ref, "url": pet_url},
                                    )
                                except Exception as db_error:
                                    logger.warning(f"Failed to save {pet_url}: {db_error}")
                                    await session.rollback()  # Rollback failed save
                                    failed += 1
                            else:
                                failed += 1
                                await url_repo.mark_failed(
                                    pet_url, animal_data.get("error", "Unknown error")
                                )

                        except Exception as e:
                            logger.error(f"Failed to scrape {pet_url}: {e}")
                            failed += 1
                            await url_repo.mark_failed(pet_url, str(e))

                except Exception as e:
                    logger.error(f"Failed to scrape listing {listing_url}: {e}")

        # Mark adopted animals (no longer in listings)
        adopted_refs = existing_refs - found_refs
        for ref in adopted_refs:
            await animal_repo.mark_adopted(ref)
            await emit_event(EventType.ANIMAL_ADOPTED, {"reference": ref})
            logger.info(f"Marked animal {ref} as adopted")

        await session.commit()

        return {
            "discovered": discovered,
            "scraped": scraped,
            "failed": failed,
            "adopted": len(adopted_refs),
        }

    async def _scrape_content(self, session, categorized: dict) -> dict:
        """Scrape general content pages with smart retry mechanism."""
        url_repo = ScrapedURLRepository(session)

        discovered = 0
        scraped = 0
        failed = 0

        # Get content URLs (general, service, tips)
        content_types = [URLType.GENERAL, URLType.SERVICE, URLType.TIPS]

        # Phase 1: Initial scraping pass
        logger.info("Phase 1: Initial content scraping pass")
        for url_type in content_types:
            urls = [cu.url for cu in categorized.get(url_type, [])]
            discovered += len(urls)

            for url in urls:
                try:
                    await url_repo.upsert(url, url_type)

                    result = await self.content_scraper.scrape_and_save(url)

                    if result.get("success"):
                        scraped += 1
                        await url_repo.mark_success(
                            url,
                            result.get("content_hash", ""),
                            result.get("file_path"),
                        )
                        await emit_event(
                            EventType.CONTENT_SAVED,
                            {"url": url, "file_path": result.get("file_path")},
                        )
                        await session.commit()  # Commit after each success
                    else:
                        failed += 1
                        await url_repo.mark_failed(url, result.get("error", "Unknown"))
                        await session.commit()  # Commit failures too
                        logger.warning(f"Failed to scrape {url}: {result.get('error', 'Unknown')}")

                except Exception as e:
                    logger.error(f"Failed to scrape content {url}: {e}")
                    failed += 1
                    try:
                        await url_repo.mark_failed(url, str(e))
                        await session.commit()  # Commit failures
                    except Exception as db_error:
                        logger.error(f"Failed to mark URL as failed: {db_error}")
                        await session.rollback()

        # Phase 2: Retry failed URLs (max 3 retries)
        logger.info(f"Phase 1 complete. Scraped: {scraped}, Failed: {failed}")

        max_retries = 3
        for retry_attempt in range(1, max_retries + 1):
            # Get failed URLs that haven't exceeded max retries
            failed_urls = await url_repo.get_failed(max_retries=max_retries)

            if not failed_urls:
                logger.info(f"No failed URLs to retry at attempt {retry_attempt}")
                break

            logger.info(f"Phase 2 - Retry attempt {retry_attempt}: Retrying {len(failed_urls)} failed URLs")

            retried = 0
            retry_success = 0

            for scraped_url in failed_urls:
                url = scraped_url.url

                try:
                    logger.info(f"Retrying {url} (attempt {scraped_url.retry_count + 1}/{max_retries})")

                    # Use longer timeout for retries
                    result = await self.content_scraper.scrape_and_save(url)

                    if result.get("success"):
                        retry_success += 1
                        scraped += 1
                        failed -= 1  # Reduce failed count
                        await url_repo.mark_success(
                            url,
                            result.get("content_hash", ""),
                            result.get("file_path"),
                        )
                        await emit_event(
                            EventType.CONTENT_SAVED,
                            {"url": url, "file_path": result.get("file_path")},
                        )
                        await session.commit()
                        logger.info(f"✓ Retry successful for {url}")
                    else:
                        await url_repo.mark_failed(url, result.get("error", "Unknown"))
                        await session.commit()
                        logger.warning(f"Retry failed for {url}: {result.get('error', 'Unknown')}")

                    retried += 1

                except Exception as e:
                    logger.error(f"Exception during retry for {url}: {e}")
                    try:
                        await url_repo.mark_failed(url, str(e))
                        await session.commit()
                    except Exception as db_error:
                        logger.error(f"Failed to mark URL as failed: {db_error}")
                        await session.rollback()

            logger.info(f"Retry attempt {retry_attempt} complete. Retried: {retried}, Successful: {retry_success}")

            # If we successfully retried some URLs, continue to next attempt for remaining failures
            if retry_success == 0 and retried > 0:
                logger.info("No successful retries in this attempt, stopping retry loop")
                break

        # Final commit in case any pending
        try:
            await session.commit()
        except Exception:
            pass  # Already committed incrementally

        logger.info(f"Content scraping complete. Total - Discovered: {discovered}, Scraped: {scraped}, Failed: {failed}")

        return {
            "discovered": discovered,
            "scraped": scraped,
            "failed": failed,
        }

    async def refresh_sitemap(self) -> list[str]:
        """Refresh the sitemap cache and return new URLs."""
        logger.info("Refreshing sitemap")
        urls = self.sitemap_crawler.discover_urls()
        return urls


def main():
    """CLI entry point for running the orchestrator."""
    import asyncio
    from ..utils.config import get_settings
    from ..utils.logging import setup_logging

    settings = get_settings()
    setup_logging(level=settings.log_level)

    orchestrator = PipelineOrchestrator(
        zyte_api_key=settings.zyte_api_key,
        use_zyte=bool(settings.zyte_api_key),
        content_dir=settings.general_content_dir,
    )

    asyncio.run(orchestrator.run_full_scrape())


if __name__ == "__main__":
    main()
