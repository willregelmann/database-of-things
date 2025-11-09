-- Rename image_url to image_key for flexible storage
ALTER TABLE entities
RENAME COLUMN image_url TO image_key;

-- Update index name
ALTER INDEX idx_entities_image_url RENAME TO idx_entities_image_key;

-- Update column comment
COMMENT ON COLUMN entities.image_key IS 'Image storage key or external URL. If starts with http/https, treated as external URL. Otherwise, treated as Supabase Storage path.';

-- Create function to generate full URLs from keys with optional transformations
-- Uses hardcoded local URL for simplicity (can be overridden in production via function replacement)
CREATE OR REPLACE FUNCTION get_image_url(image_key TEXT, width INT DEFAULT NULL, height INT DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE
  base_url TEXT := 'http://127.0.0.1:54321/storage/v1/object/public';
  transform_params TEXT := '';
BEGIN
  IF image_key IS NULL THEN
    RETURN NULL;
  ELSIF image_key LIKE 'http%' THEN
    -- External URLs can't be transformed via Supabase
    RETURN image_key;
  ELSE
    -- Add transformation parameters if provided
    IF width IS NOT NULL THEN
      transform_params := transform_params || '?width=' || width::TEXT;
    END IF;
    IF height IS NOT NULL THEN
      IF transform_params = '' THEN
        transform_params := '?height=' || height::TEXT;
      ELSE
        transform_params := transform_params || '&height=' || height::TEXT;
      END IF;
    END IF;

    RETURN base_url || '/' || image_key || transform_params;
  END IF;
END;
$$ LANGUAGE plpgsql STABLE;
