"""Health check and admin routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends

from ..schemas import HealthResponse, ScrapeJobRequest, ScrapeJobResponse, SyncRequest, SyncResponse
from ...pipeline.orchestrator import PipelineOrchestrator
from ...sync.content_uploader import ContentUploader
from ...utils.config import get_settings

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


@admin_router.get("/stats")
async def get_admin_stats() -> dict:
    """Get system statistics."""
    from ...database.session import get_session
    from ...database.repositories.animal_repository import AnimalRepository
    from ...database.repositories.scrape_repository import ScrapeJobRepository

    async with get_session() as session:
        animal_repo = AnimalRepository(session)
        job_repo = ScrapeJobRepository(session)

        # Get animal counts
        species_counts = await animal_repo.count_by_species()
        total_animals = sum(species_counts.values())

        # Get recent jobs
        latest_job = await job_repo.get_latest()

        return {
            "animals": {
                "total": total_animals,
                "by_species": species_counts,
            },
            "latest_job": {
                "id": latest_job.id if latest_job else None,
                "type": latest_job.job_type.value if latest_job else None,
                "status": latest_job.status.value if latest_job else None,
                "started_at": latest_job.started_at.isoformat() if latest_job and latest_job.started_at else None,
            } if latest_job else None,
        }
