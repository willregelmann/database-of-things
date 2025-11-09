-- Add source_url column to entities table for attribution
-- This makes source URLs easily queryable and indexable

-- Add the column
ALTER TABLE entities
ADD COLUMN source_url TEXT;

-- Migrate existing source URLs from attributes JSONB to dedicated column
UPDATE entities
SET source_url = attributes->>'source_url'
WHERE attributes->>'source_url' IS NOT NULL;

-- Remove source_url from attributes to avoid duplication
UPDATE entities
SET attributes = attributes - 'source_url'
WHERE attributes ? 'source_url';

-- Add index for querying by source
CREATE INDEX idx_entities_source_url ON entities(source_url) WHERE source_url IS NOT NULL;

-- Add comment
COMMENT ON COLUMN entities.source_url IS 'URL of the source page where this entity''s data was obtained (for attribution)';
