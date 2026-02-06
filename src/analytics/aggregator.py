"""Analytics aggregation service for pre-calculating daily/hourly metrics."""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Conversation, ConversationMessage, ConversationAnalytics
from ..database.repositories.conversation_repository import (
    ConversationRepository,
    ConversationMessageRepository,
    ConversationAnalyticsRepository,
)
from .topic_extractor import Topic, extract_topic

logger = logging.getLogger(__name__)


class AnalyticsAggregator:
    """Aggregate conversation data into daily analytics."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = ConversationMessageRepository(session)
        self.analytics_repo = ConversationAnalyticsRepository(session)

    async def aggregate_date(self, target_date: date) -> ConversationAnalytics:
        """
        Aggregate all conversations for a specific date.
        
        Returns the ConversationAnalytics entry for that date.
        """
        logger.info(f"Aggregating analytics for date: {target_date}")
        
        # Get or create analytics entry
        analytics = await self.analytics_repo.get_or_create_by_date(target_date)
        
        # Get all conversations for this date
        conversations = await self.conv_repo.get_conversations_by_date_range(
            target_date, target_date
        )
        
        # Calculate basic metrics
        total_conversations = len(conversations)
        total_messages = sum(conv.message_count for conv in conversations)
        unique_sessions = len(set(conv.session_id for conv in conversations))
        
        # Calculate averages
        avg_messages = (
            total_messages / total_conversations
            if total_conversations > 0
            else 0.0
        )
        
        durations = [
            conv.duration_seconds
            for conv in conversations
            if conv.duration_seconds is not None
        ]
        avg_duration = (
            sum(durations) / len(durations)
            if durations
            else 0.0
        )
        
        # Language distribution
        language_en = sum(1 for conv in conversations if conv.language == "en")
        language_fr = sum(1 for conv in conversations if conv.language == "fr")
        
        # Topic distribution - get all user messages for this date
        topic_counts = {
            Topic.ADOPTION: 0,
            Topic.ANIMALS: 0,
            Topic.SERVICES: 0,
            Topic.HOURS_LOCATION: 0,
            Topic.FEES: 0,
            Topic.GENERAL: 0,
        }
        
        # Get all user messages for conversations on this date
        for conversation in conversations:
            messages = await self.msg_repo.get_by_conversation_id(conversation.id)
            for msg in messages:
                if msg.role == "user":
                    topic = extract_topic(msg.content)
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Update analytics entry
        analytics.total_conversations = total_conversations
        analytics.total_messages = total_messages
        analytics.avg_messages_per_conversation = int(avg_messages)
        analytics.avg_duration_seconds = int(avg_duration)
        analytics.unique_sessions = unique_sessions
        analytics.language_en = language_en
        analytics.language_fr = language_fr
        analytics.topic_adoption = topic_counts[Topic.ADOPTION]
        analytics.topic_animals = topic_counts[Topic.ANIMALS]
        analytics.topic_services = topic_counts[Topic.SERVICES]
        analytics.topic_hours_location = topic_counts[Topic.HOURS_LOCATION]
        analytics.topic_fees = topic_counts[Topic.FEES]
        analytics.topic_general = topic_counts[Topic.GENERAL]
        
        await self.analytics_repo.update(analytics)
        await self.session.commit()
        
        logger.info(
            f"Aggregated {target_date}: {total_conversations} conversations, "
            f"{total_messages} messages"
        )
        
        return analytics

    async def aggregate_date_range(
        self, start_date: date, end_date: date
    ) -> list[ConversationAnalytics]:
        """Aggregate analytics for a date range."""
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            analytics = await self.aggregate_date(current_date)
            results.append(analytics)
            current_date += timedelta(days=1)
        
        return results

    async def aggregate_yesterday(self) -> ConversationAnalytics:
        """Aggregate analytics for yesterday (most common use case)."""
        yesterday = date.today() - timedelta(days=1)
        return await self.aggregate_date(yesterday)

    async def aggregate_today(self) -> ConversationAnalytics:
        """Aggregate analytics for today (partial data)."""
        today = date.today()
        return await self.aggregate_date(today)

    async def get_topic_distribution(
        self, start_date: date, end_date: date
    ) -> Dict[str, int]:
        """Get topic distribution for a date range."""
        analytics_list = await self.analytics_repo.get_by_date_range(
            start_date, end_date
        )
        
        return {
            "adoption": sum(a.topic_adoption for a in analytics_list),
            "animals": sum(a.topic_animals for a in analytics_list),
            "services": sum(a.topic_services for a in analytics_list),
            "hours_location": sum(a.topic_hours_location for a in analytics_list),
            "fees": sum(a.topic_fees for a in analytics_list),
            "general": sum(a.topic_general for a in analytics_list),
        }

    async def get_animal_interest(
        self, start_date: date, end_date: date, limit: int = 20
    ) -> list[tuple[str, int]]:
        """
        Get most asked-about animals by reference number.
        
        Returns list of (reference_number, count) tuples.
        """
        # Get all user messages in date range
        conversations = await self.conv_repo.get_conversations_by_date_range(
            start_date, end_date
        )
        
        from .animal_tracker import get_animal_tracker
        tracker = get_animal_tracker()
        
        # Count references
        ref_counts: Dict[str, int] = {}
        
        for conversation in conversations:
            messages = await self.msg_repo.get_by_conversation_id(conversation.id)
            for msg in messages:
                if msg.role == "user":
                    ref_num = tracker.extract_reference_number(msg.content)
                    if ref_num:
                        ref_counts[ref_num] = ref_counts.get(ref_num, 0) + 1
        
        # Sort by count and return top N
        sorted_refs = sorted(
            ref_counts.items(), key=lambda x: x[1], reverse=True
        )[:limit]
        
        return sorted_refs
