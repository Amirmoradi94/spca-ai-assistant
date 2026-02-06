"""Repository for Conversation data access."""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple

from sqlalchemy import select, update, delete, func, and_, or_, extract, Integer, cast
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import Conversation, ConversationMessage, ConversationAnalytics


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_session_id(self, session_id: str) -> Optional[Conversation]:
        """Get conversation by session ID."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[Conversation]:
        """Get all conversations with pagination."""
        result = await self.session.execute(
            select(Conversation)
            .order_by(Conversation.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation."""
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def update(self, conversation: Conversation) -> Conversation:
        """Update an existing conversation."""
        await self.session.merge(conversation)
        await self.session.flush()
        return conversation

    async def delete(self, id: int) -> bool:
        """Delete a conversation by ID."""
        result = await self.session.execute(
            delete(Conversation).where(Conversation.id == id)
        )
        return result.rowcount > 0

    async def get_or_create_by_session_id(
        self, session_id: str, language: str = "en", **kwargs
    ) -> Tuple[Conversation, bool]:
        """Get existing conversation or create new one."""
        conversation = await self.get_by_session_id(session_id)
        if conversation:
            return conversation, False
        
        conversation = Conversation(
            session_id=session_id,
            language=language,
            started_at=datetime.utcnow(),
            **kwargs
        )
        conversation = await self.create(conversation)
        return conversation, True

    async def end_conversation(self, session_id: str) -> Optional[Conversation]:
        """End a conversation by setting ended_at and calculating duration."""
        conversation = await self.get_by_session_id(session_id)
        if conversation:
            conversation.ended_at = datetime.utcnow()
            if conversation.started_at:
                duration = (conversation.ended_at - conversation.started_at).total_seconds()
                conversation.duration_seconds = int(duration)
            await self.session.flush()
        return conversation

    async def increment_message_count(self, session_id: str) -> None:
        """Increment message count for a conversation."""
        await self.session.execute(
            update(Conversation)
            .where(Conversation.session_id == session_id)
            .values(message_count=Conversation.message_count + 1)
        )

    async def get_active_conversations(self) -> int:
        """Get count of active conversations (not ended)."""
        result = await self.session.execute(
            select(func.count(Conversation.id))
            .where(Conversation.ended_at.is_(None))
        )
        return result.scalar() or 0

    async def get_conversations_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Conversation]:
        """Get conversations within a date range."""
        result = await self.session.execute(
            select(Conversation)
            .where(
                and_(
                    func.date(Conversation.started_at) >= start_date,
                    func.date(Conversation.started_at) <= end_date
                )
            )
            .order_by(Conversation.started_at.desc())
        )
        return list(result.scalars().all())

    async def get_stats_by_date_range(
        self, start_date: date, end_date: date
    ) -> Dict:
        """Get aggregated statistics for a date range."""
        result = await self.session.execute(
            select(
                func.count(Conversation.id).label("total_conversations"),
                func.sum(Conversation.message_count).label("total_messages"),
                func.avg(Conversation.message_count).label("avg_messages"),
                func.avg(Conversation.duration_seconds).label("avg_duration"),
                func.count(func.distinct(Conversation.session_id)).label("unique_sessions"),
                func.sum(cast(Conversation.language == "en", Integer)).label("language_en"),
                func.sum(cast(Conversation.language == "fr", Integer)).label("language_fr"),
            )
            .where(
                and_(
                    func.date(Conversation.started_at) >= start_date,
                    func.date(Conversation.started_at) <= end_date
                )
            )
        )
        row = result.first()
        return {
            "total_conversations": row.total_conversations or 0,
            "total_messages": row.total_messages or 0,
            "avg_messages_per_conversation": float(row.avg_messages or 0),
            "avg_duration_seconds": float(row.avg_duration or 0),
            "unique_sessions": row.unique_sessions or 0,
            "language_en": row.language_en or 0,
            "language_fr": row.language_fr or 0,
        }

    async def get_conversations_by_hour(
        self, start_date: date, end_date: date
    ) -> List[Tuple[int, int]]:
        """Get conversation count grouped by hour of day."""
        result = await self.session.execute(
            select(
                extract("hour", Conversation.started_at).label("hour"),
                func.count(Conversation.id).label("count")
            )
            .where(
                and_(
                    func.date(Conversation.started_at) >= start_date,
                    func.date(Conversation.started_at) <= end_date
                )
            )
            .group_by(extract("hour", Conversation.started_at))
            .order_by("hour")
        )
        return [(row.hour, row.count) for row in result.all()]

    async def get_conversations_by_day(
        self, start_date: date, end_date: date
    ) -> List[Tuple[date, int]]:
        """Get conversation count grouped by day."""
        result = await self.session.execute(
            select(
                func.date(Conversation.started_at).label("day"),
                func.count(Conversation.id).label("count")
            )
            .where(
                and_(
                    func.date(Conversation.started_at) >= start_date,
                    func.date(Conversation.started_at) <= end_date
                )
            )
            .group_by(func.date(Conversation.started_at))
            .order_by("day")
        )
        return [(row.day, row.count) for row in result.all()]


class ConversationMessageRepository:
    """Repository for ConversationMessage operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: ConversationMessage) -> ConversationMessage:
        """Create a new message."""
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_by_conversation_id(
        self, conversation_id: int, limit: int = 100
    ) -> List[ConversationMessage]:
        """Get all messages for a conversation."""
        result = await self.session.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.timestamp.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_first_messages(
        self, limit: int = 100
    ) -> List[ConversationMessage]:
        """Get first messages from conversations (for common questions analysis)."""
        # This requires a subquery to get the first message per conversation
        subquery = (
            select(
                ConversationMessage.conversation_id,
                func.min(ConversationMessage.timestamp).label("first_timestamp")
            )
            .where(ConversationMessage.role == "user")
            .group_by(ConversationMessage.conversation_id)
            .subquery()
        )
        
        result = await self.session.execute(
            select(ConversationMessage)
            .join(
                subquery,
                and_(
                    ConversationMessage.conversation_id == subquery.c.conversation_id,
                    ConversationMessage.timestamp == subquery.c.first_timestamp
                )
            )
            .order_by(ConversationMessage.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_common_questions(
        self, limit: int = 20
    ) -> List[Tuple[str, int]]:
        """Get most common user questions."""
        result = await self.session.execute(
            select(
                ConversationMessage.content,
                func.count(ConversationMessage.id).label("count")
            )
            .where(ConversationMessage.role == "user")
            .group_by(ConversationMessage.content)
            .order_by(func.count(ConversationMessage.id).desc())
            .limit(limit)
        )
        return [(row.content, row.count) for row in result.all()]


class ConversationAnalyticsRepository:
    """Repository for ConversationAnalytics operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_date(self, analytics_date: date) -> Optional[ConversationAnalytics]:
        """Get analytics for a specific date."""
        result = await self.session.execute(
            select(ConversationAnalytics)
            .where(ConversationAnalytics.date == analytics_date)
        )
        return result.scalar_one_or_none()

    async def get_or_create_by_date(
        self, analytics_date: date
    ) -> ConversationAnalytics:
        """Get existing analytics or create new entry for date."""
        analytics = await self.get_by_date(analytics_date)
        if analytics:
            return analytics
        
        analytics = ConversationAnalytics(date=analytics_date)
        self.session.add(analytics)
        await self.session.flush()
        await self.session.refresh(analytics)
        return analytics

    async def get_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[ConversationAnalytics]:
        """Get analytics for a date range."""
        result = await self.session.execute(
            select(ConversationAnalytics)
            .where(
                and_(
                    ConversationAnalytics.date >= start_date,
                    ConversationAnalytics.date <= end_date
                )
            )
            .order_by(ConversationAnalytics.date.asc())
        )
        return list(result.scalars().all())

    async def update(self, analytics: ConversationAnalytics) -> ConversationAnalytics:
        """Update analytics entry."""
        await self.session.merge(analytics)
        await self.session.flush()
        return analytics
