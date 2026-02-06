-- Migration: Add conversation tracking tables
-- Created: 2026-01-28
-- Description: Adds tables for tracking conversations, messages, and analytics

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    message_count INTEGER NOT NULL DEFAULT 0,
    duration_seconds INTEGER,
    user_ip_hash VARCHAR(64),
    user_agent VARCHAR(500),
    referrer VARCHAR(500)
);

-- Create indexes for conversations
CREATE INDEX IF NOT EXISTS ix_conversations_session_id ON conversations(session_id);
CREATE INDEX IF NOT EXISTS ix_conversations_started_at ON conversations(started_at);
CREATE INDEX IF NOT EXISTS ix_conversations_language ON conversations(language);

-- Create conversation_messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    response_time_ms INTEGER,
    sources_count INTEGER,
    error_occurred BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Create indexes for conversation_messages
CREATE INDEX IF NOT EXISTS ix_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_conversation_messages_timestamp ON conversation_messages(timestamp);

-- Create conversation_analytics table
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_conversations INTEGER NOT NULL DEFAULT 0,
    total_messages INTEGER NOT NULL DEFAULT 0,
    avg_messages_per_conversation INTEGER NOT NULL DEFAULT 0,
    avg_duration_seconds INTEGER NOT NULL DEFAULT 0,
    unique_sessions INTEGER NOT NULL DEFAULT 0,
    language_en INTEGER NOT NULL DEFAULT 0,
    language_fr INTEGER NOT NULL DEFAULT 0,
    topic_adoption INTEGER NOT NULL DEFAULT 0,
    topic_animals INTEGER NOT NULL DEFAULT 0,
    topic_services INTEGER NOT NULL DEFAULT 0,
    topic_hours_location INTEGER NOT NULL DEFAULT 0,
    topic_fees INTEGER NOT NULL DEFAULT 0,
    topic_general INTEGER NOT NULL DEFAULT 0
);

-- Create index for conversation_analytics
CREATE INDEX IF NOT EXISTS ix_conversation_analytics_date ON conversation_analytics(date);

-- Add comments for documentation
COMMENT ON TABLE conversations IS 'Tracks individual chat conversations/sessions';
COMMENT ON TABLE conversation_messages IS 'Stores individual messages within conversations';
COMMENT ON TABLE conversation_analytics IS 'Pre-aggregated daily analytics for fast dashboard queries';

COMMENT ON COLUMN conversations.user_ip_hash IS 'Hashed IP address for privacy (SHA256 hash)';
COMMENT ON COLUMN conversation_messages.response_time_ms IS 'Response time in milliseconds for assistant messages';
COMMENT ON COLUMN conversation_messages.sources_count IS 'Number of file search sources used in the response';
