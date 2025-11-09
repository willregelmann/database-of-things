-- Add thumbnail_url column for pre-generated thumbnails
-- This column stores paths to optimized 300x300 WebP thumbnails
-- Reduces image bandwidth by 90-95% for list views and grids
-- Works on Supabase Free Tier (no Pro Plan required)

-- Add the column
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS thumbnail_url TEXT;

-- Create partial index (only for non-null values)
CREATE INDEX IF NOT EXISTS idx_entities_thumbnail_url
ON entities(thumbnail_url)
WHERE thumbnail_url IS NOT NULL;

-- Add documentation
COMMENT ON COLUMN entities.thumbnail_url IS 'Pre-generated thumbnail path (typically 300x300 WebP) - e.g., /storage/v1/object/public/images/thumbnails/uuid.webp. Provides 90-95% size reduction vs original images.';
