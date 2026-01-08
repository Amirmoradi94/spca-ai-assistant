-- Migration: Add content_hash column to sync_log table
-- Created: 2026-01-08
-- Description: Adds content_hash field for deduplication and change detection

-- Add content_hash column to sync_log table
ALTER TABLE sync_log
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

-- Add comment for documentation
COMMENT ON COLUMN sync_log.content_hash IS 'SHA256 hash of content for change detection and deduplication';
