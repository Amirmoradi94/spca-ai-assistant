"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID (optional)")
    language: str = Field("en", description="Language: 'en' or 'fr'")
    context: Optional[dict] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Do you have any dogs available for adoption?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "language": "en"
            }
        }


class SourceInfo(BaseModel):
    """Information about a source citation."""
    file: str
    snippet: str


class ChatResponse(BaseModel):
    """Response from the chatbot."""
    response: str = Field(..., description="Chatbot response")
    session_id: str = Field(..., description="Session ID")
    sources: list[SourceInfo] = Field(default_factory=list, description="Source citations")
    suggested_questions: list[str] = Field(default_factory=list, description="Suggested follow-up questions")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Yes! We currently have several dogs available for adoption...",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "sources": [
                    {
                        "file": "animal_2000064570.txt",
                        "snippet": "Logan is a friendly dog..."
                    }
                ],
                "suggested_questions": [
                    "What are the adoption fees?",
                    "What are your opening hours?"
                ]
            }
        }


class SessionInfo(BaseModel):
    """Information about a chat session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    language: str
    message_count: int
    is_active: bool

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-01-05T10:30:00",
                "last_activity": "2024-01-05T10:35:00",
                "language": "en",
                "message_count": 5,
                "is_active": True
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str = "spca-chatbot"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "spca-chatbot",
                "timestamp": "2024-01-05T10:30:00",
                "version": "1.0.0"
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid session ID",
                "detail": "Session not found or expired",
                "timestamp": "2024-01-05T10:30:00"
            }
        }


class ScrapeJobRequest(BaseModel):
    """Request to trigger a scrape job."""
    job_type: str = Field(..., description="Job type: 'animals', 'content', or 'full'")

    class Config:
        json_schema_extra = {
            "example": {
                "job_type": "animals"
            }
        }


class ScrapeJobResponse(BaseModel):
    """Response from a scrape job."""
    job_id: int
    status: str
    urls_discovered: Optional[int] = None
    urls_scraped: Optional[int] = None
    urls_failed: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": 123,
                "status": "completed",
                "urls_discovered": 50,
                "urls_scraped": 48,
                "urls_failed": 2
            }
        }


class SyncRequest(BaseModel):
    """Request to trigger a sync operation."""
    sync_type: str = Field("all", description="Sync type: 'animals', 'content', or 'all'")

    class Config:
        json_schema_extra = {
            "example": {
                "sync_type": "animals"
            }
        }


class SyncResponse(BaseModel):
    """Response from a sync operation."""
    status: str
    synced: int
    failed: int

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "synced": 45,
                "failed": 2
            }
        }
