"""Repository for Scrape job and URL tracking."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import ScrapeJob, ScrapedURL, SyncLog, JobStatus, JobType, ScrapeStatus, URLType


class ScrapeJobRepository(BaseRepository[ScrapeJob]):
    """Repository for ScrapeJob operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> Optional[ScrapeJob]:
        """Get job by ID."""
        result = await self.session.execute(
            select(ScrapeJob).where(ScrapeJob.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ScrapeJob]:
        """Get all jobs with pagination."""
        result = await self.session.execute(
            select(ScrapeJob)
            .order_by(ScrapeJob.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_running(self) -> List[ScrapeJob]:
        """Get all running jobs."""
        result = await self.session.execute(
            select(ScrapeJob).where(ScrapeJob.status == JobStatus.RUNNING)
        )
        return list(result.scalars().all())

    async def get_latest(self, job_type: Optional[JobType] = None) -> Optional[ScrapeJob]:
        """Get the latest job, optionally filtered by type."""
        query = select(ScrapeJob).order_by(ScrapeJob.started_at.desc()).limit(1)
        if job_type:
            query = query.where(ScrapeJob.job_type == job_type)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, job: ScrapeJob) -> ScrapeJob:
        """Create a new job."""
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def update(self, job: ScrapeJob) -> ScrapeJob:
        """Update a job."""
        await self.session.merge(job)
        await self.session.flush()
        return job

    async def delete(self, id: int) -> bool:
        """Delete a job by ID."""
        result = await self.session.execute(
            delete(ScrapeJob).where(ScrapeJob.id == id)
        )
        return result.rowcount > 0

    async def start_job(self, job_type: JobType) -> ScrapeJob:
        """Create and start a new job."""
        job = ScrapeJob(
            job_type=job_type,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def complete_job(
        self,
        job_id: int,
        urls_discovered: int = 0,
        urls_scraped: int = 0,
        urls_failed: int = 0,
    ) -> None:
        """Mark a job as completed."""
        await self.session.execute(
            update(ScrapeJob)
            .where(ScrapeJob.id == job_id)
            .values(
                status=JobStatus.COMPLETED,
                completed_at=datetime.utcnow(),
                urls_discovered=urls_discovered,
                urls_scraped=urls_scraped,
                urls_failed=urls_failed,
            )
        )

    async def fail_job(self, job_id: int, error_message: str) -> None:
        """Mark a job as failed."""
        await self.session.execute(
            update(ScrapeJob)
            .where(ScrapeJob.id == job_id)
            .values(
                status=JobStatus.FAILED,
                completed_at=datetime.utcnow(),
                error_message=error_message,
            )
        )


class ScrapedURLRepository(BaseRepository[ScrapedURL]):
    """Repository for ScrapedURL operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> Optional[ScrapedURL]:
        """Get URL by ID."""
        result = await self.session.execute(
            select(ScrapedURL).where(ScrapedURL.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_url(self, url: str) -> Optional[ScrapedURL]:
        """Get by URL string."""
        result = await self.session.execute(
            select(ScrapedURL).where(ScrapedURL.url == url)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ScrapedURL]:
        """Get all URLs with pagination."""
        result = await self.session.execute(
            select(ScrapedURL)
            .order_by(ScrapedURL.last_scraped_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_type(self, url_type: URLType, limit: int = 1000) -> List[ScrapedURL]:
        """Get URLs by type."""
        result = await self.session.execute(
            select(ScrapedURL)
            .where(ScrapedURL.url_type == url_type)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending(self, url_type: Optional[URLType] = None, limit: int = 100) -> List[ScrapedURL]:
        """Get pending URLs to scrape."""
        query = select(ScrapedURL).where(ScrapedURL.scrape_status == ScrapeStatus.PENDING)
        if url_type:
            query = query.where(ScrapedURL.url_type == url_type)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_failed(self, max_retries: int = 3) -> List[ScrapedURL]:
        """Get failed URLs that can be retried."""
        result = await self.session.execute(
            select(ScrapedURL)
            .where(ScrapedURL.scrape_status == ScrapeStatus.FAILED)
            .where(ScrapedURL.retry_count < max_retries)
        )
        return list(result.scalars().all())

    async def create(self, scraped_url: ScrapedURL) -> ScrapedURL:
        """Create a new scraped URL record."""
        self.session.add(scraped_url)
        await self.session.flush()
        await self.session.refresh(scraped_url)
        return scraped_url

    async def update(self, scraped_url: ScrapedURL) -> ScrapedURL:
        """Update a scraped URL."""
        await self.session.merge(scraped_url)
        await self.session.flush()
        return scraped_url

    async def delete(self, id: int) -> bool:
        """Delete a URL by ID."""
        result = await self.session.execute(
            delete(ScrapedURL).where(ScrapedURL.id == id)
        )
        return result.rowcount > 0

    async def upsert(self, url: str, url_type: URLType, job_id: Optional[int] = None) -> ScrapedURL:
        """Insert or update URL record."""
        existing = await self.get_by_url(url)
        if existing:
            existing.url_type = url_type
            if job_id:
                existing.job_id = job_id
            await self.session.flush()
            return existing
        else:
            scraped_url = ScrapedURL(
                url=url,
                url_type=url_type,
                job_id=job_id,
                scrape_status=ScrapeStatus.PENDING,
            )
            self.session.add(scraped_url)
            await self.session.flush()
            await self.session.refresh(scraped_url)
            return scraped_url

    async def mark_success(
        self, url: str, content_hash: str, file_path: Optional[str] = None
    ) -> None:
        """Mark URL as successfully scraped."""
        await self.session.execute(
            update(ScrapedURL)
            .where(ScrapedURL.url == url)
            .values(
                scrape_status=ScrapeStatus.SUCCESS,
                last_scraped_at=datetime.utcnow(),
                content_hash=content_hash,
                file_path=file_path,
                error_message=None,
            )
        )

    async def mark_failed(self, url: str, error_message: str) -> None:
        """Mark URL as failed."""
        scraped = await self.get_by_url(url)
        if scraped:
            await self.session.execute(
                update(ScrapedURL)
                .where(ScrapedURL.url == url)
                .values(
                    scrape_status=ScrapeStatus.FAILED,
                    retry_count=scraped.retry_count + 1,
                    error_message=error_message,
                )
            )


class SyncLogRepository(BaseRepository[SyncLog]):
    """Repository for SyncLog operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> Optional[SyncLog]:
        """Get log by ID."""
        result = await self.session.execute(
            select(SyncLog).where(SyncLog.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[SyncLog]:
        """Get all logs with pagination."""
        result = await self.session.execute(
            select(SyncLog)
            .order_by(SyncLog.synced_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, log: SyncLog) -> SyncLog:
        """Create a new sync log."""
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def update(self, log: SyncLog) -> SyncLog:
        """Update a sync log."""
        await self.session.merge(log)
        await self.session.flush()
        return log

    async def delete(self, id: int) -> bool:
        """Delete a log by ID."""
        result = await self.session.execute(
            delete(SyncLog).where(SyncLog.id == id)
        )
        return result.rowcount > 0

    async def log_sync(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        google_file_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        content_hash: Optional[str] = None,
    ) -> SyncLog:
        """Create a sync log entry."""
        log = SyncLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            google_file_id=google_file_id,
            status=status,
            error_message=error_message,
            content_hash=content_hash,
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def get_by_entity(self, entity_type: str, entity_id: str) -> List[SyncLog]:
        """Get logs for a specific entity."""
        result = await self.session.execute(
            select(SyncLog)
            .where(SyncLog.entity_type == entity_type)
            .where(SyncLog.entity_id == entity_id)
            .order_by(SyncLog.synced_at.desc())
        )
        return list(result.scalars().all())
