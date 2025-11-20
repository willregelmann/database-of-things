-- ============================================
-- SIMPLIFY SCHEMA: Convert to enums and drop relationship types
-- ============================================

-- 1. Create entity_type enum
CREATE TYPE entity_type AS ENUM ('item', 'collection');

-- 2. Convert entities.type from TEXT to entity_type enum
-- First, add a temporary column with the enum type
ALTER TABLE entities ADD COLUMN type_new entity_type;

-- Convert all existing types to the new enum values
-- 'collection' stays as 'collection', everything else becomes 'item'
UPDATE entities SET type_new = CASE
  WHEN type = 'collection' THEN 'collection'::entity_type
  ELSE 'item'::entity_type
END;

-- Drop dependent objects first
DROP VIEW IF EXISTS entities_missing_embeddings CASCADE;
DROP TRIGGER IF EXISTS trigger_validate_card_attributes ON entities;
DROP FUNCTION IF EXISTS validate_card_attributes() CASCADE;

-- Drop the old TEXT column
ALTER TABLE entities DROP COLUMN type;

-- Rename the new column to type
ALTER TABLE entities RENAME COLUMN type_new TO type;

-- Make it NOT NULL
ALTER TABLE entities ALTER COLUMN type SET NOT NULL;

-- Recreate the index on type
DROP INDEX IF EXISTS idx_entities_type;
CREATE INDEX idx_entities_type ON entities(type);

-- 3. Drop relationships.type column
-- First, drop indexes that reference the type column
DROP INDEX IF EXISTS idx_relationships_from_type;
DROP INDEX IF EXISTS idx_relationships_to_type;

-- Drop the type column
ALTER TABLE relationships DROP COLUMN type;

-- Recreate indexes without the type column
CREATE INDEX idx_relationships_from_id ON relationships(from_id);
CREATE INDEX idx_relationships_to_id ON relationships(to_id);

-- Update the unique constraint to not include type
ALTER TABLE relationships DROP CONSTRAINT IF EXISTS relationships_from_id_to_id_type_key;
ALTER TABLE relationships ADD CONSTRAINT relationships_from_id_to_id_key UNIQUE(from_id, to_id);

-- Drop the attributes index (column was already removed in migration 20251024195010)
DROP INDEX IF EXISTS idx_relationships_attributes;
