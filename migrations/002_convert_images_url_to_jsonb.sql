-- Migration: Convert images_url from json to jsonb
-- This allows using jsonb functions like jsonb_array_length

-- Convert images_url column from json to jsonb
ALTER TABLE animals
ALTER COLUMN images_url TYPE jsonb USING images_url::jsonb;

-- Add comment
COMMENT ON COLUMN animals.images_url IS 'Array of image URLs in JSONB format';
