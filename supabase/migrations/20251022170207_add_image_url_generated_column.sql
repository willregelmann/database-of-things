-- Add image_url column to entities table
-- This will be automatically populated by a trigger whenever image_key changes

ALTER TABLE entities
ADD COLUMN image_url TEXT;

-- Create trigger function to automatically compute image_url from image_key
CREATE OR REPLACE FUNCTION update_entity_image_url()
RETURNS TRIGGER AS $$
BEGIN
  NEW.image_url := get_image_url(NEW.image_key);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger that fires before INSERT or UPDATE
CREATE TRIGGER entities_image_url_trigger
BEFORE INSERT OR UPDATE OF image_key ON entities
FOR EACH ROW
EXECUTE FUNCTION update_entity_image_url();

-- Populate image_url for all existing rows
UPDATE entities
SET image_url = get_image_url(image_key);

-- Add index on image_url for faster queries
CREATE INDEX idx_entities_image_url ON entities(image_url) WHERE image_url IS NOT NULL;

-- Add comment
COMMENT ON COLUMN entities.image_url IS 'Computed full URL for images. Automatically updated when image_key changes. External URLs returned as-is, storage paths converted to Supabase Storage URLs.';

-- Note: We're keeping the entities_with_urls view for backwards compatibility
-- but the base entities table now has image_url directly
