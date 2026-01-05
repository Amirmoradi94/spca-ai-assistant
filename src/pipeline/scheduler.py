"""Job scheduler for automated scraping."""

import asyncio
import logging
import signal
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .orchestrator import PipelineOrchestrator
from .events import EventType, get_event_emitter
from ..utils.config import get_settings, get_yaml_config
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


class ScrapeScheduler:
    """Manages scheduled scraping jobs."""

    def __init__(
        self,
        orchestrator: Optional[PipelineOrchestrator] = None,
    ):
        self.settings = get_settings()
        self.yaml_config = get_yaml_config()

        self.orchestrator = orchestrator or PipelineOrchestrator(
            zyte_api_key=self.settings.zyte_api_key,
            use_zyte=bool(self.settings.zyte_api_key),
            content_dir=self.settings.general_content_dir,
        )

        self.scheduler = AsyncIOScheduler()
        self._running = False

    def setup_schedules(self) -> None:
        """Configure all scheduled jobs."""
        # Get schedule config
        animal_hours = self.yaml_config.get("scheduling.animal_scrape_hours", 4)
        content_hour = self.yaml_config.get("scheduling.content_scrape_hour", 2)
        sitemap_day = self.yaml_config.get("scheduling.sitemap_refresh_day", "sun")

        # Animals: Scrape every N hours (default: 4)
        self.scheduler.add_job(
            self._run_animal_scrape,
            IntervalTrigger(hours=animal_hours),
            id="animal_scrape",
            name="Animal Pages Scrape",
            replace_existing=True,
        )
        logger.info(f"Scheduled animal scrape every {animal_hours} hours")

        # General content: Daily at specified hour (default: 2 AM)
        self.scheduler.add_job(
            self._run_content_scrape,
            CronTrigger(hour=content_hour, minute=0),
            id="content_scrape",
            name="General Content Scrape",
            replace_existing=True,
        )
        logger.info(f"Scheduled content scrape daily at {content_hour}:00")

        # Sitemap refresh: Weekly on specified day (default: Sunday 1 AM)
        self.scheduler.add_job(
            self._run_sitemap_refresh,
            CronTrigger(day_of_week=sitemap_day, hour=1, minute=0),
            id="sitemap_refresh",
            name="Sitemap Refresh",
            replace_existing=True,
        )
        logger.info(f"Scheduled sitemap refresh on {sitemap_day} at 1:00")

    async def _run_animal_scrape(self) -> None:
        """Run animal scrape job."""
        logger.info("Running scheduled animal scrape")
        try:
            result = await self.orchestrator.run_animal_scrape()
            logger.info(f"Animal scrape completed: {result}")
        except Exception as e:
            logger.error(f"Scheduled animal scrape failed: {e}")

    async def _run_content_scrape(self) -> None:
        """Run content scrape job."""
        logger.info("Running scheduled content scrape")
        try:
            result = await self.orchestrator.run_content_scrape()
            logger.info(f"Content scrape completed: {result}")
        except Exception as e:
            logger.error(f"Scheduled content scrape failed: {e}")

    async def _run_sitemap_refresh(self) -> None:
        """Run sitemap refresh."""
        logger.info("Running scheduled sitemap refresh")
        try:
            urls = await self.orchestrator.refresh_sitemap()
            logger.info(f"Sitemap refresh completed: {len(urls)} URLs")
        except Exception as e:
            logger.error(f"Scheduled sitemap refresh failed: {e}")

    def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self.setup_schedules()
            self.scheduler.start()
            self._running = True
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        """Shutdown the scheduler."""
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Scheduler stopped")

    async def trigger_immediate(self, job_type: str) -> dict:
        """Trigger an immediate run of a specific job type."""
        logger.info(f"Triggering immediate {job_type} job")

        if job_type == "animals":
            return await self.orchestrator.run_animal_scrape()
        elif job_type == "content":
            return await self.orchestrator.run_content_scrape()
        elif job_type == "full":
            return await self.orchestrator.run_full_scrape()
        else:
            raise ValueError(f"Unknown job type: {job_type}")


async def run_scheduler() -> None:
    """Run the scheduler as a standalone service."""
    settings = get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    logger.info("Starting SPCA Scraper Scheduler")

    scheduler = ScrapeScheduler()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    # Start scheduler
    scheduler.start()

    # Run an initial animal scrape on startup
    logger.info("Running initial animal scrape")
    try:
        await scheduler.trigger_immediate("animals")
    except Exception as e:
        logger.error(f"Initial scrape failed: {e}")

    # Wait for shutdown
    await shutdown_event.wait()

    # Cleanup
    scheduler.shutdown()
    logger.info("Scheduler shutdown complete")


def main():
    """Entry point for scheduler service."""
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
