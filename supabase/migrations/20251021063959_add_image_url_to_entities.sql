-- Add image_url column to entities table
ALTER TABLE entities
ADD COLUMN image_url TEXT;

-- Add index for image lookups (optional but useful)
CREATE INDEX idx_entities_image_url ON entities(image_url) WHERE image_url IS NOT NULL;

-- Add comment explaining the column
COMMENT ON COLUMN entities.image_url IS 'Primary/canonical image URL for this entity. Additional images can be stored in attributes JSONB.';
