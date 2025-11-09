-- Add external_ids JSONB column to entities table
-- This column stores mappings to external system IDs (e.g., Pokemon TCG API, IGDB, etc.)

ALTER TABLE entities
ADD COLUMN external_ids JSONB DEFAULT '{}'::jsonb;

-- Add GIN index for efficient JSONB queries
CREATE INDEX idx_entities_external_ids ON entities USING GIN (external_ids);

-- Add comment for documentation
COMMENT ON COLUMN entities.external_ids IS 'External system IDs (e.g., {"tcgplayer": "base1-4", "pokemontcg_io": "base1-4"})';
