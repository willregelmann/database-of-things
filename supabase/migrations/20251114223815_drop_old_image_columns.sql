-- Drop old image_url and thumbnail_url columns from entities, variants, and components
-- Now that data has been migrated to the images table with primary_image_id foreign keys

-- Drop dependent views first
DROP VIEW IF EXISTS entity_data_quality_issues CASCADE;
DROP VIEW IF EXISTS entities_with_image_urls CASCADE;

-- Drop old image columns from entities
-- Also drop image_key which was an older column name
ALTER TABLE entities DROP COLUMN IF EXISTS image_url;
ALTER TABLE entities DROP COLUMN IF EXISTS thumbnail_url;
ALTER TABLE entities DROP COLUMN IF EXISTS image_key;

-- Drop old image columns from variants
ALTER TABLE variants DROP COLUMN IF EXISTS image_url;
ALTER TABLE variants DROP COLUMN IF EXISTS thumbnail_url;

-- Drop old image columns from components
ALTER TABLE components DROP COLUMN IF EXISTS image_url;
ALTER TABLE components DROP COLUMN IF EXISTS thumbnail_url;

-- Report completion
DO $$
BEGIN
  RAISE NOTICE 'Old image columns dropped successfully';
  RAISE NOTICE 'Images now managed exclusively through images table';
END $$;
