"""Chat session management."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ChatSession:
    """A chat session with history."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    language: str = "en"
    messages: list[ChatMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if session has expired (1 hour default)."""
        return datetime.utcnow() - self.last_activity > timedelta(hours=1)

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def add_message(self, role: str, content: str) -> ChatMessage:
        """Add a message to the session."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        return message

    def get_history(self, limit: int = 20) -> list[dict]:
        """Get recent message history for context."""
        recent = self.messages[-limit:] if limit else self.messages
        return [
            {"role": msg.role, "parts": [msg.content]}
            for msg in recent
        ]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "language": self.language,
            "message_count": self.message_count,
            "is_active": not self.is_expired,
        }


class SessionManager:
    """Manages chat sessions with automatic cleanup."""

    def __init__(
        self,
        max_sessions: int = 10000,
        expiry_hours: int = 1,
        cleanup_interval: int = 300,
    ):
        self.sessions: dict[str, ChatSession] = {}
        self.max_sessions = max_sessions
        self.expiry_hours = expiry_hours
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the cleanup background task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    def create_session(self, language: str = "en") -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        session = ChatSession(
            session_id=session_id,
            created_at=now,
            last_activity=now,
            language=language,
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID, updating last activity."""
        session = self.sessions.get(session_id)
        if session and not session.is_expired:
            session.last_activity = datetime.utcnow()
            return session
        return None

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        language: str = "en",
    ) -> ChatSession:
        """Get existing session or create new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session(language=language)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Optional[ChatMessage]:
        """Add a message to a session."""
        session = self.get_session(session_id)
        if session:
            return session.add_message(role, content)
        return None

    def end_session(self, session_id: str) -> bool:
        """End and remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired sessions."""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            await self._cleanup_expired()

    async def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        async with self._lock:
            expired = [
                sid for sid, session in self.sessions.items()
                if session.is_expired
            ]
            for sid in expired:
                del self.sessions[sid]

            if expired:
                import logging
                logging.getLogger(__name__).info(
                    f"Cleaned up {len(expired)} expired sessions"
                )


# Global session manager singleton
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
