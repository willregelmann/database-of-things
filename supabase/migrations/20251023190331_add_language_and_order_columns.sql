-- ================================================================
-- Migration: Add language and order columns
-- ================================================================
-- This migration safely extracts commonly-used fields from JSONB
-- attributes into dedicated columns for better performance and
-- simpler queries.
--
-- SAFETY: This migration is non-destructive:
-- - Does NOT remove data from attributes JSONB
-- - Does NOT drop or truncate any tables
-- - Only adds new columns and populates them
-- ================================================================

-- ================================================================
-- STEP 1: Add new columns to entities table
-- ================================================================

-- Add language column (nullable, matches country column type)
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS language CHAR(2);

COMMENT ON COLUMN entities.language IS 'ISO 639-1 language code (e.g., "en", "ja", "es"). Extracted from attributes for better query performance.';

-- ================================================================
-- STEP 2: Add new columns to relationships table
-- ================================================================

-- Add order column (nullable integer for ordering items in collections)
ALTER TABLE relationships
ADD COLUMN IF NOT EXISTS "order" INTEGER;

COMMENT ON COLUMN relationships."order" IS 'Sort order for relationships (e.g., card number in a set). Extracted from attributes for better query performance.';

-- ================================================================
-- STEP 3: Populate language column from existing attributes
-- ================================================================

-- Populate language from attributes->>'language'
-- Only updates rows where language is currently NULL and attributes has a language value
UPDATE entities
SET language = attributes->>'language'
WHERE language IS NULL
  AND attributes->>'language' IS NOT NULL;

-- ================================================================
-- STEP 4: Populate order column from existing attributes
-- ================================================================

-- Populate order from attributes->>'order'
-- Only updates rows where order is currently NULL and attributes has a valid integer order value
UPDATE relationships
SET "order" = (attributes->>'order')::INTEGER
WHERE "order" IS NULL
  AND attributes->>'order' IS NOT NULL
  AND attributes->>'order' ~ '^-?[0-9]+$'; -- Regex to ensure it's a valid integer

-- ================================================================
-- STEP 5: Create indexes for performance
-- ================================================================

-- Index on language for filtering (e.g., "show me all English cards")
CREATE INDEX IF NOT EXISTS idx_entities_language ON entities(language)
WHERE language IS NOT NULL;

-- Index on order for sorting relationships
CREATE INDEX IF NOT EXISTS idx_relationships_order ON relationships("order")
WHERE "order" IS NOT NULL;

-- ================================================================
-- STEP 6: Verification queries (output for migration log)
-- ================================================================

-- Show counts before/after for verification
DO $$
DECLARE
    entities_with_language INTEGER;
    relationships_with_order INTEGER;
BEGIN
    SELECT COUNT(*) INTO entities_with_language
    FROM entities
    WHERE language IS NOT NULL;

    SELECT COUNT(*) INTO relationships_with_order
    FROM relationships
    WHERE "order" IS NOT NULL;

    RAISE NOTICE ' Migration completed successfully';
    RAISE NOTICE '  - Entities with language: %', entities_with_language;
    RAISE NOTICE '  - Relationships with order: %', relationships_with_order;
END $$;
