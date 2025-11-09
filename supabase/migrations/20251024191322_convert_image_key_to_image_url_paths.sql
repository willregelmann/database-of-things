-- Convert image_key to image_url with path-based storage
-- This migration:
-- 1. Drops dependent objects (views, triggers, functions)
-- 2. Adds image_url column
-- 3. Migrates data from image_key to image_url, converting local storage paths
-- 4. Drops image_key column and its index
-- 5. Removes get_image_url() function (no longer needed with paths)

-- Drop dependent objects first
DROP VIEW IF EXISTS entities_with_urls CASCADE;
DROP TRIGGER IF EXISTS entities_image_url_trigger ON entities;
DROP FUNCTION IF EXISTS update_entity_image_url() CASCADE;

-- Add image_url column if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'entities' AND column_name = 'image_url') THEN
    ALTER TABLE entities ADD COLUMN image_url TEXT;
  END IF;
END $$;

-- Migrate data from image_key to image_url
-- Convert: images/uuid.ext � /storage/v1/object/public/images/uuid.ext
-- Keep external URLs as-is
UPDATE entities
SET image_url = CASE
  -- Local storage paths: images/* � /storage/v1/object/public/images/*
  WHEN image_key LIKE 'images/%' THEN '/storage/v1/object/public/' || image_key
  -- External URLs: keep as-is
  WHEN image_key LIKE 'http://%' OR image_key LIKE 'https://%' THEN image_key
  -- Anything else: keep as-is
  ELSE image_key
END
WHERE image_key IS NOT NULL;

-- Drop the old image_key column and its index
DROP INDEX IF EXISTS idx_entities_image_key;
ALTER TABLE entities DROP COLUMN image_key;

-- Create index on image_url (partial index, only for non-null values)
CREATE INDEX idx_entities_image_url ON entities(image_url) WHERE image_url IS NOT NULL;

-- Drop the get_image_url() function (no longer needed - store full paths)
DROP FUNCTION IF EXISTS get_image_url(TEXT, INT, INT);
DROP FUNCTION IF EXISTS get_image_url(TEXT);

-- Add comment to document the column
COMMENT ON COLUMN entities.image_url IS 'Image URL path. Local storage uses paths like /storage/v1/object/public/images/uuid.ext, external URLs stored as-is.';
