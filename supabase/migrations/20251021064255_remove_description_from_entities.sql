-- Remove description column from entities table
-- Description can be stored in attributes JSONB if needed
ALTER TABLE entities
DROP COLUMN description;

-- Update full-text search index to only use name
DROP INDEX IF EXISTS idx_entities_search;
CREATE INDEX idx_entities_search ON entities USING gin(
  to_tsvector('english', coalesce(name, ''))
);
