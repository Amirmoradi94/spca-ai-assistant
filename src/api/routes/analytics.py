"""Analytics API routes for dashboard data."""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.session import get_db_session
from ...database.models import Conversation, ConversationMessage, ConversationAnalytics
from ...database.repositories.conversation_repository import (
    ConversationRepository,
    ConversationMessageRepository,
    ConversationAnalyticsRepository,
)
from ...analytics.aggregator import AnalyticsAggregator
from ...analytics.topic_extractor import Topic, extract_topic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


def parse_date_range(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 7,
) -> tuple[date, date]:
    """Parse date range from query parameters."""
    if end_date:
        end = datetime.fromisoformat(end_date).date()
    else:
        end = date.today()
    
    if start_date:
        start = datetime.fromisoformat(start_date).date()
    else:
        start = end - timedelta(days=days - 1)
    
    return start, end


@router.get("/overview")
async def get_overview(
    days: int = Query(7, ge=1, le=365),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get overview statistics."""
    try:
        start_date, end_date = parse_date_range(days=days)
        conv_repo = ConversationRepository(db_session)
        
        # Get stats for date range
        stats = await conv_repo.get_stats_by_date_range(start_date, end_date)
        
        # Get active conversations right now
        active_now = await conv_repo.get_active_conversations()
        
        # Get peak hours data
        peak_hours = await conv_repo.get_conversations_by_hour(start_date, end_date)
        peak_hours_dict = {hour: count for hour, count in peak_hours}
        
        # Fill in missing hours with 0
        for hour in range(24):
            if hour not in peak_hours_dict:
                peak_hours_dict[hour] = 0
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "total_conversations": stats["total_conversations"],
            "active_conversations": active_now,
            "total_messages": stats["total_messages"],
            "avg_messages_per_conversation": round(stats["avg_messages_per_conversation"], 2),
            "avg_duration_seconds": round(stats["avg_duration_seconds"], 2),
            "unique_sessions": stats["unique_sessions"],
            "language_distribution": {
                "en": stats["language_en"],
                "fr": stats["language_fr"],
            },
            "peak_hours": [
                {"hour": hour, "count": peak_hours_dict[hour]}
                for hour in sorted(peak_hours_dict.keys())
            ],
        }
    except Exception as e:
        logger.error(f"Error getting overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def get_topics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get topic distribution and trends."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        aggregator = AnalyticsAggregator(db_session)
        
        # Get topic distribution
        topic_dist = await aggregator.get_topic_distribution(start, end)
        
        # Get topic trends over time
        analytics_list = await aggregator.analytics_repo.get_by_date_range(start, end)
        
        trends = []
        for analytics in analytics_list:
            trends.append({
                "date": analytics.date.isoformat(),
                "adoption": analytics.topic_adoption,
                "animals": analytics.topic_animals,
                "services": analytics.topic_services,
                "hours_location": analytics.topic_hours_location,
                "fees": analytics.topic_fees,
                "general": analytics.topic_general,
            })
        
        # Get most common questions by topic
        msg_repo = ConversationMessageRepository(db_session)
        conv_repo = ConversationRepository(db_session)
        conversations = await conv_repo.get_conversations_by_date_range(start, end)
        
        questions_by_topic = {
            "adoption": [],
            "animals": [],
            "services": [],
            "hours_location": [],
            "fees": [],
            "general": [],
        }
        
        question_counts: dict[str, dict[str, int]] = {
            topic: {} for topic in questions_by_topic.keys()
        }
        
        for conversation in conversations:
            messages = await msg_repo.get_by_conversation_id(conversation.id)
            for msg in messages:
                if msg.role == "user":
                    topic = extract_topic(msg.content)
                    topic_key = topic.value
                    content = msg.content.lower().strip()
                    question_counts[topic_key][content] = (
                        question_counts[topic_key].get(content, 0) + 1
                    )
        
        # Get top 5 questions per topic
        for topic_key in questions_by_topic.keys():
            sorted_questions = sorted(
                question_counts[topic_key].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            questions_by_topic[topic_key] = [
                {"question": q, "count": c} for q, c in sorted_questions
            ]
        
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "distribution": topic_dist,
            "trends": trends,
            "common_questions": questions_by_topic,
        }
    except Exception as e:
        logger.error(f"Error getting topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/animals")
async def get_animal_interest(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    limit: int = Query(20, ge=1, le=100),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get animal interest statistics."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        aggregator = AnalyticsAggregator(db_session)
        
        # Get most asked-about animals
        animal_refs = await aggregator.get_animal_interest(start, end, limit)
        
        # Get species popularity
        conv_repo = ConversationRepository(db_session)
        msg_repo = ConversationMessageRepository(db_session)
        conversations = await conv_repo.get_conversations_by_date_range(start, end)
        
        from ...analytics.animal_tracker import get_animal_tracker
        tracker = get_animal_tracker()
        
        species_counts = {}
        for conversation in conversations:
            messages = await msg_repo.get_by_conversation_id(conversation.id)
            for msg in messages:
                if msg.role == "user":
                    message_lower = msg.content.lower()
                    if "dog" in message_lower or "chien" in message_lower:
                        species_counts["dog"] = species_counts.get("dog", 0) + 1
                    if "cat" in message_lower or "chat" in message_lower:
                        species_counts["cat"] = species_counts.get("cat", 0) + 1
                    if "rabbit" in message_lower or "lapin" in message_lower:
                        species_counts["rabbit"] = species_counts.get("rabbit", 0) + 1
                    if "bird" in message_lower or "oiseau" in message_lower:
                        species_counts["bird"] = species_counts.get("bird", 0) + 1
        
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "top_animals": [
                {"reference_number": ref, "query_count": count}
                for ref, count in animal_refs
            ],
            "species_popularity": species_counts,
        }
    except Exception as e:
        logger.error(f"Error getting animal interest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline")
async def get_timeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    granularity: str = Query("daily", regex="^(daily|hourly)$"),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get timeline data for conversations and messages."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        conv_repo = ConversationRepository(db_session)
        
        if granularity == "daily":
            # Get conversations by day
            daily_data = await conv_repo.get_conversations_by_day(start, end)
            
            # Get messages by day
            result = await db_session.execute(
                select(
                    func.date(ConversationMessage.timestamp).label("day"),
                    func.count(ConversationMessage.id).label("count")
                )
                .where(
                    and_(
                        func.date(ConversationMessage.timestamp) >= start,
                        func.date(ConversationMessage.timestamp) <= end
                    )
                )
                .group_by(func.date(ConversationMessage.timestamp))
                .order_by("day")
            )
            messages_by_day = {row.day: row.count for row in result.all()}
            
            # Combine data
            timeline = []
            for day, conv_count in daily_data:
                timeline.append({
                    "date": day.isoformat(),
                    "conversations": conv_count,
                    "messages": messages_by_day.get(day, 0),
                })
            
            return {
                "granularity": "daily",
                "period": {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                },
                "timeline": timeline,
            }
        else:
            # Hourly granularity
            # This would require more complex querying
            return {
                "granularity": "hourly",
                "message": "Hourly granularity not yet implemented",
            }
    except Exception as e:
        logger.error(f"Error getting timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engagement")
async def get_engagement(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get engagement metrics."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        conv_repo = ConversationRepository(db_session)
        conversations = await conv_repo.get_conversations_by_date_range(start, end)
        
        # Calculate metrics
        total_conversations = len(conversations)
        completed = sum(1 for c in conversations if c.ended_at is not None)
        completion_rate = (
            (completed / total_conversations * 100)
            if total_conversations > 0
            else 0
        )
        
        # Message count distribution
        message_counts = [c.message_count for c in conversations]
        bounce_count = sum(1 for c in message_counts if c == 1)
        deep_engagement = sum(1 for c in message_counts if c >= 5)
        
        bounce_rate = (
            (bounce_count / total_conversations * 100)
            if total_conversations > 0
            else 0
        )
        
        # Duration distribution
        durations = [
            c.duration_seconds
            for c in conversations
            if c.duration_seconds is not None
        ]
        
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "total_conversations": total_conversations,
            "completed_conversations": completed,
            "completion_rate": round(completion_rate, 2),
            "avg_messages_per_conversation": (
                sum(message_counts) / len(message_counts)
                if message_counts
                else 0
            ),
            "bounce_rate": round(bounce_rate, 2),
            "bounce_count": bounce_count,
            "deep_engagement_count": deep_engagement,
            "deep_engagement_rate": (
                (deep_engagement / total_conversations * 100)
                if total_conversations > 0
                else 0
            ),
            "avg_duration_seconds": (
                sum(durations) / len(durations)
                if durations
                else 0
            ),
            "message_count_distribution": {
                "1": sum(1 for c in message_counts if c == 1),
                "2-4": sum(1 for c in message_counts if 2 <= c <= 4),
                "5-9": sum(1 for c in message_counts if 5 <= c <= 9),
                "10+": sum(1 for c in message_counts if c >= 10),
            },
        }
    except Exception as e:
        logger.error(f"Error getting engagement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/questions")
async def get_questions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    limit: int = Query(10, ge=1, le=50),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get question patterns."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        msg_repo = ConversationMessageRepository(db_session)
        
        # Get first messages (first questions)
        first_messages = await msg_repo.get_first_messages(limit * 10)
        
        # Filter by date range
        first_questions = []
        for msg in first_messages:
            if start <= msg.timestamp.date() <= end:
                first_questions.append(msg.content)
        
        # Count occurrences
        first_question_counts: dict[str, int] = {}
        for question in first_questions:
            question_lower = question.lower().strip()
            first_question_counts[question_lower] = (
                first_question_counts.get(question_lower, 0) + 1
            )
        
        # Get most common first questions
        top_first = sorted(
            first_question_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Get most common questions overall
        common_questions = await msg_repo.get_common_questions(limit)
        
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "top_first_questions": [
                {"question": q, "count": c} for q, c in top_first
            ],
            "top_questions_overall": [
                {"question": q, "count": c} for q, c in common_questions
            ],
        }
    except Exception as e:
        logger.error(f"Error getting questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    days: int = 30,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get performance metrics."""
    try:
        start, end = parse_date_range(start_date, end_date, days)
        
        # Get all assistant messages in date range
        result = await db_session.execute(
            select(
                func.avg(ConversationMessage.response_time_ms).label("avg_response_time"),
                func.count(ConversationMessage.id).label("total_responses"),
                func.sum(func.cast(ConversationMessage.error_occurred, func.Integer)).label("error_count"),
                func.avg(ConversationMessage.sources_count).label("avg_sources"),
            )
            .where(
                and_(
                    ConversationMessage.role == "assistant",
                    func.date(ConversationMessage.timestamp) >= start,
                    func.date(ConversationMessage.timestamp) <= end
                )
            )
        )
        row = result.first()
        
        total_responses = row.total_responses or 0
        error_count = row.error_count or 0
        error_rate = (
            (error_count / total_responses * 100)
            if total_responses > 0
            else 0
        )
        
        return {
            "period": {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            "avg_response_time_ms": round(row.avg_response_time or 0, 2),
            "total_responses": total_responses,
            "error_count": error_count,
            "error_rate": round(error_rate, 2),
            "avg_sources_per_response": round(row.avg_sources or 0, 2),
        }
    except Exception as e:
        logger.error(f"Error getting performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
