"""Health check and admin routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from ..schemas import HealthResponse, ScrapeJobRequest, ScrapeJobResponse, SyncRequest, SyncResponse
from ...pipeline.orchestrator import PipelineOrchestrator
from ...sync.content_uploader import ContentUploader
from ...utils.config import get_settings
from ...database.models import ScrapeStatus, URLType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the status of the API service.
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        service="spca-chatbot",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
    )


@router.get("/", response_model=dict)
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "service": "SPCA AI Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/v1/chat",
            "health": "/health",
            "docs": "/docs",
        }
    }


# Admin routes (should be protected in production)
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@admin_router.post("/scrape", response_model=ScrapeJobResponse)
async def trigger_scrape(request: ScrapeJobRequest) -> ScrapeJobResponse:
    """
    Trigger a scrape job manually.

    Job types:
    - 'animals': Scrape only animal pages
    - 'content': Scrape only general content
    - 'full': Full scrape (sitemap + animals + content)

    **Note:** This endpoint should be protected in production.
    """
    settings = get_settings()

    orchestrator = PipelineOrchestrator(
        zyte_api_key=settings.zyte_api_key,
        use_zyte=bool(settings.zyte_api_key),
        content_dir=settings.general_content_dir,
    )

    try:
        if request.job_type == "animals":
            result = await orchestrator.run_animal_scrape()
        elif request.job_type == "content":
            result = await orchestrator.run_content_scrape()
        elif request.job_type == "full":
            result = await orchestrator.run_full_scrape()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid job type: {request.job_type}. Must be 'animals', 'content', or 'full'"
            )

        return ScrapeJobResponse(**result)

    except Exception as e:
        logger.error(f"Scrape job failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Scrape job failed: {str(e)}"
        )


@admin_router.post("/sync", response_model=SyncResponse)
async def trigger_sync(request: SyncRequest) -> SyncResponse:
    """
    Trigger a sync to Google File Search.

    Sync types:
    - 'animals': Sync only animals
    - 'content': Sync only content files
    - 'all': Sync everything

    **Note:** This endpoint should be protected in production.
    """
    settings = get_settings()

    uploader = ContentUploader(
        api_key=settings.google_api_key,
        content_dir=settings.general_content_dir,
        batch_size=settings.sync_batch_size,
    )

    try:
        if request.sync_type == "animals":
            result = await uploader.sync_all_animals()
            return SyncResponse(
                status="completed",
                synced=result["synced"],
                failed=result["failed"],
            )
        elif request.sync_type == "content":
            result = await uploader.sync_content_files()
            return SyncResponse(
                status="completed",
                synced=result["synced"],
                failed=result["failed"],
            )
        elif request.sync_type == "all":
            result = await uploader.full_sync()
            total_synced = result["animals"]["synced"] + result["content"]["synced"]
            total_failed = result["animals"]["failed"] + result["content"]["failed"]
            return SyncResponse(
                status="completed",
                synced=total_synced,
                failed=total_failed,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sync type: {request.sync_type}"
            )

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {str(e)}"
        )


@admin_router.post("/retry-failed", response_model=dict)
async def retry_failed_urls() -> dict:
    """
    Retry failed content scraping URLs.

    This endpoint manually triggers a retry of all URLs that failed during scraping
    and haven't exceeded the maximum retry limit (3 attempts).

    **Note:** This endpoint should be protected in production.
    """
    from ...database.session import get_session
    from ...database.repositories.scrape_repository import ScrapedURLRepository
    from ...scrapers.content_scraper import ContentScraper
    from ...utils.config import get_settings

    settings = get_settings()
    scraper = ContentScraper(content_dir=settings.general_content_dir)

    async with get_session() as session:
        url_repo = ScrapedURLRepository(session)

        # Get failed URLs that can be retried
        failed_urls = await url_repo.get_failed(max_retries=3)

        if not failed_urls:
            return {
                "status": "completed",
                "message": "No failed URLs to retry",
                "retried": 0,
                "successful": 0,
                "failed": 0,
            }

        logger.info(f"Retrying {len(failed_urls)} failed URLs")

        retried = 0
        successful = 0
        still_failed = 0

        for scraped_url in failed_urls:
            url = scraped_url.url

            try:
                logger.info(f"Retrying {url} (attempt {scraped_url.retry_count + 1}/3)")

                result = await scraper.scrape_and_save(url)

                if result.get("success"):
                    successful += 1
                    await url_repo.mark_success(
                        url,
                        result.get("content_hash", ""),
                        result.get("file_path"),
                    )
                    await session.commit()
                    logger.info(f"✓ Retry successful for {url}")
                else:
                    still_failed += 1
                    await url_repo.mark_failed(url, result.get("error", "Unknown"))
                    await session.commit()
                    logger.warning(f"Retry failed for {url}: {result.get('error', 'Unknown')}")

                retried += 1

            except Exception as e:
                logger.error(f"Exception during retry for {url}: {e}")
                still_failed += 1
                try:
                    await url_repo.mark_failed(url, str(e))
                    await session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to mark URL as failed: {db_error}")
                    await session.rollback()

        return {
            "status": "completed",
            "message": f"Retry complete. {successful} succeeded, {still_failed} still failed",
            "retried": retried,
            "successful": successful,
            "failed": still_failed,
        }


@admin_router.get("/stats")
async def get_admin_stats() -> dict:
    """Get system statistics."""
    from ...database.session import get_session
    from ...database.repositories.animal_repository import AnimalRepository
    from ...database.repositories.scrape_repository import ScrapeJobRepository
    from sqlalchemy import select, func
    from ...database.models import Animal, ScrapeJob, ScrapedURL, SyncLog

    async with get_session() as session:
        animal_repo = AnimalRepository(session)
        job_repo = ScrapeJobRepository(session)

        # Get animal counts
        species_counts = await animal_repo.count_by_species()
        total_animals = sum(species_counts.values())

        # Get synced count
        synced_result = await session.execute(
            select(func.count(Animal.id)).where(Animal.synced_to_google == True)
        )
        synced_count = synced_result.scalar() or 0

        # Get recent jobs (last 5)
        jobs_result = await session.execute(
            select(ScrapeJob).order_by(ScrapeJob.id.desc()).limit(5)
        )
        recent_jobs = jobs_result.scalars().all()

        # Get latest job
        latest_job = await job_repo.get_latest()

        # Get URL stats
        url_stats_result = await session.execute(
            select(
                ScrapedURL.scrape_status,
                func.count(ScrapedURL.id)
            ).group_by(ScrapedURL.scrape_status)
        )
        url_stats = {status: count for status, count in url_stats_result.all()}

        # Get failed URLs that can be retried (retry_count < 3)
        from ...database.repositories.scrape_repository import ScrapedURLRepository
        url_repo = ScrapedURLRepository(session)
        retryable_urls = await url_repo.get_failed(max_retries=3)
        retryable_count = len(retryable_urls)

        # Get content file stats
        content_stats_result = await session.execute(
            select(
                ScrapedURL.url_type,
                func.count(ScrapedURL.id)
            ).where(ScrapedURL.scrape_status == ScrapeStatus.SUCCESS)
            .where(ScrapedURL.url_type.in_([URLType.GENERAL, URLType.SERVICE, URLType.TIPS]))
            .group_by(ScrapedURL.url_type)
        )
        content_by_type = {url_type.value: count for url_type, count in content_stats_result.all()}
        total_content = sum(content_by_type.values())

        # Get sync stats - get latest syncs by entity type
        sync_animals_result = await session.execute(
            select(SyncLog).where(SyncLog.entity_type == "animal").order_by(SyncLog.id.desc()).limit(1)
        )
        latest_animal_sync = sync_animals_result.scalar_one_or_none()

        sync_content_result = await session.execute(
            select(SyncLog).where(SyncLog.entity_type == "content").order_by(SyncLog.id.desc()).limit(1)
        )
        latest_content_sync = sync_content_result.scalar_one_or_none()

        return {
            "animals": {
                "total": total_animals,
                "synced": synced_count,
                "by_species": species_counts,
            },
            "content": {
                "total": total_content,
                "by_type": content_by_type,
            },
            "scrape_jobs": {
                "total": len(recent_jobs),
                "recent": [
                    {
                        "id": job.id,
                        "type": job.job_type.value,
                        "status": job.status.value,
                        "started_at": job.started_at.isoformat() if job.started_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "urls_discovered": job.urls_discovered,
                        "urls_scraped": job.urls_scraped,
                        "urls_failed": job.urls_failed,
                    }
                    for job in recent_jobs
                ],
            },
            "urls": {
                "by_status": url_stats,
                "retryable_failed": retryable_count,
            },
            "latest_sync": {
                "animals": {
                    "entity_type": latest_animal_sync.entity_type if latest_animal_sync else None,
                    "status": latest_animal_sync.status if latest_animal_sync else None,
                    "synced_at": latest_animal_sync.synced_at.isoformat() if latest_animal_sync and latest_animal_sync.synced_at else None,
                } if latest_animal_sync else None,
                "content": {
                    "entity_type": latest_content_sync.entity_type if latest_content_sync else None,
                    "status": latest_content_sync.status if latest_content_sync else None,
                    "synced_at": latest_content_sync.synced_at.isoformat() if latest_content_sync and latest_content_sync.synced_at else None,
                } if latest_content_sync else None,
            }
        }


@admin_router.post("/fix-stale-jobs")
async def fix_stale_jobs() -> dict:
    """
    Fix stale scrape jobs that are stuck in 'running' status.

    This endpoint marks jobs that have been running for more than 1 hour
    as completed or failed based on their results.

    **Note:** This endpoint should be protected in production.
    """
    from ...database.session import get_session
    from ...database.repositories.scrape_repository import ScrapeJobRepository
    from sqlalchemy import select
    from ...database.models import ScrapeJob, JobStatus
    from datetime import datetime, timedelta, timezone

    async with get_session() as session:
        job_repo = ScrapeJobRepository(session)

        # Find jobs that are "running" for more than 1 hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await session.execute(
            select(ScrapeJob).where(
                ScrapeJob.status == JobStatus.RUNNING,
                ScrapeJob.started_at < one_hour_ago
            )
        )
        stale_jobs = result.scalars().all()

        if not stale_jobs:
            return {
                "status": "success",
                "message": "No stale jobs found",
                "fixed": 0
            }

        fixed = 0
        for job in stale_jobs:
            # If job has some scraped URLs, mark as completed
            # Otherwise mark as failed
            if job.urls_scraped > 0:
                job.status = JobStatus.COMPLETED
                job.completed_at = job.started_at + timedelta(minutes=30)  # Estimate
                logger.info(f"Marked job {job.id} as COMPLETED (had {job.urls_scraped} scraped URLs)")
            else:
                job.status = JobStatus.FAILED
                job.completed_at = job.started_at + timedelta(minutes=5)
                job.error_message = "Job timed out or crashed"
                logger.info(f"Marked job {job.id} as FAILED (no scraped URLs)")

            fixed += 1

        await session.commit()

        return {
            "status": "success",
            "message": f"Fixed {fixed} stale jobs",
            "fixed": fixed,
            "jobs": [
                {
                    "id": job.id,
                    "type": job.job_type.value,
                    "new_status": job.status.value
                }
                for job in stale_jobs
            ]
        }


@admin_router.get("/tables/{table_name}")
async def get_table_data(table_name: str, limit: int = 50, offset: int = 0) -> dict:
    """
    Get data from a specific database table.

    Available tables:
    - animals
    - scrape_jobs
    - scraped_urls
    - sync_log

    **Note:** This endpoint should be protected in production.
    """
    from ...database.session import get_session
    from sqlalchemy import select, func
    from ...database.models import Animal, ScrapeJob, ScrapedURL, SyncLog

    # Map table names to models
    table_map = {
        "animals": Animal,
        "scrape_jobs": ScrapeJob,
        "scraped_urls": ScrapedURL,
        "sync_log": SyncLog,
    }

    if table_name not in table_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid table name. Available tables: {', '.join(table_map.keys())}"
        )

    model = table_map[table_name]

    async with get_session() as session:
        # Get total count
        count_result = await session.execute(select(func.count(model.id)))
        total_count = count_result.scalar() or 0

        # Get paginated data
        result = await session.execute(
            select(model).order_by(model.id.desc()).limit(limit).offset(offset)
        )
        rows = result.scalars().all()

        # Convert to dict
        data = []
        for row in rows:
            row_dict = {}
            for column in row.__table__.columns:
                value = getattr(row, column.name)
                # Convert enum values to strings
                if hasattr(value, 'value'):
                    value = value.value
                # Convert datetime to ISO format
                elif hasattr(value, 'isoformat'):
                    value = value.isoformat()
                row_dict[column.name] = value
            data.append(row_dict)

        return {
            "table": table_name,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "data": data,
        }
