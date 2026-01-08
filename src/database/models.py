"""SQLAlchemy async models for SPCA AI Assistant."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AnimalStatus(str, enum.Enum):
    """Status of an animal."""
    AVAILABLE = "available"
    ADOPTED = "adopted"
    PENDING = "pending"
    HOLD = "hold"


class ScrapeStatus(str, enum.Enum):
    """Status of a scrape operation."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class JobStatus(str, enum.Enum):
    """Status of a scrape job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, enum.Enum):
    """Type of scrape job."""
    FULL = "full"
    ANIMALS_ONLY = "animals_only"
    CONTENT_ONLY = "content_only"
    INCREMENTAL = "incremental"


class URLType(str, enum.Enum):
    """Type of URL."""
    ANIMAL = "animal"
    ADOPTION_LIST = "adoption_list"
    GENERAL = "general"
    SERVICE = "service"
    TIPS = "tips"
    IGNORED = "ignored"


class Animal(Base):
    """Model for animal data."""

    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reference_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    species: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[Optional[str]] = mapped_column(String(50))
    age_category: Mapped[Optional[str]] = mapped_column(String(20))  # Young, Adult, Senior
    sex: Mapped[Optional[str]] = mapped_column(String(20))
    breed: Mapped[Optional[str]] = mapped_column(String(200))
    size: Mapped[Optional[str]] = mapped_column(String(10))  # S, M, L, XL
    color: Mapped[Optional[str]] = mapped_column(String(100))
    weight: Mapped[Optional[str]] = mapped_column(String(50))
    declawed: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    images_url: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[AnimalStatus] = mapped_column(
        Enum(AnimalStatus), default=AnimalStatus.AVAILABLE, index=True
    )

    # Metadata
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))

    # Sync tracking
    synced_to_google: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    google_file_id: Mapped[Optional[str]] = mapped_column(String(100))
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_animals_species_status", "species", "status"),
    )

    def __repr__(self) -> str:
        return f"<Animal(id={self.id}, name='{self.name}', species='{self.species}')>"


class ScrapeJob(Base):
    """Model for tracking scrape jobs."""

    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    urls_discovered: Mapped[int] = mapped_column(Integer, default=0)
    urls_scraped: Mapped[int] = mapped_column(Integer, default=0)
    urls_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # Relationship to scraped URLs
    scraped_urls: Mapped[list["ScrapedURL"]] = relationship(
        "ScrapedURL", back_populates="job", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ScrapeJob(id={self.id}, type='{self.job_type}', status='{self.status}')>"


class ScrapedURL(Base):
    """Model for tracking scraped URLs."""

    __tablename__ = "scraped_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    url_type: Mapped[URLType] = mapped_column(Enum(URLType), nullable=False, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scrape_status: Mapped[ScrapeStatus] = mapped_column(
        Enum(ScrapeStatus), default=ScrapeStatus.PENDING, index=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Foreign key to job
    job_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("scrape_jobs.id"), index=True
    )
    job: Mapped[Optional["ScrapeJob"]] = relationship("ScrapeJob", back_populates="scraped_urls")

    def __repr__(self) -> str:
        return f"<ScrapedURL(id={self.id}, url='{self.url[:50]}...', type='{self.url_type}')>"


class SyncLog(Base):
    """Model for tracking sync operations to Google File Search."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'animal' or 'content'
    entity_id: Mapped[str] = mapped_column(String(500), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # 'create', 'update', 'delete'
    google_file_id: Mapped[Optional[str]] = mapped_column(String(100))
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))  # SHA256 hash for change detection
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(20), default="success")
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("ix_sync_log_entity", "entity_type", "entity_id"),
    )

    def __repr__(self) -> str:
        return f"<SyncLog(id={self.id}, entity='{self.entity_type}:{self.entity_id}')>"
