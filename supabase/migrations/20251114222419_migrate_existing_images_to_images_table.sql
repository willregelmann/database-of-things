-- Migrate existing image_url/thumbnail_url data from entities, variants, and components
-- into the new images table and set primary_image_id foreign keys

-- Migrate entity images
WITH new_entity_images AS (
  INSERT INTO images (image_url, thumbnail_url, source_url)
  SELECT
    image_url,
    thumbnail_url,
    source_url
  FROM entities
  WHERE image_url IS NOT NULL
  RETURNING id, image_url, thumbnail_url
)
UPDATE entities e
SET primary_image_id = nei.id
FROM new_entity_images nei
WHERE e.image_url = nei.image_url
  AND (e.thumbnail_url = nei.thumbnail_url OR (e.thumbnail_url IS NULL AND nei.thumbnail_url IS NULL));

-- Migrate variant images
WITH new_variant_images AS (
  INSERT INTO images (image_url, thumbnail_url)
  SELECT
    image_url,
    thumbnail_url
  FROM variants
  WHERE image_url IS NOT NULL
  RETURNING id, image_url, thumbnail_url
)
UPDATE variants v
SET primary_image_id = nvi.id
FROM new_variant_images nvi
WHERE v.image_url = nvi.image_url
  AND (v.thumbnail_url = nvi.thumbnail_url OR (v.thumbnail_url IS NULL AND nvi.thumbnail_url IS NULL));

-- Migrate component images
WITH new_component_images AS (
  INSERT INTO images (image_url, thumbnail_url)
  SELECT
    image_url,
    thumbnail_url
  FROM components
  WHERE image_url IS NOT NULL
  RETURNING id, image_url, thumbnail_url
)
UPDATE components c
SET primary_image_id = nci.id
FROM new_component_images nci
WHERE c.image_url = nci.image_url
  AND (c.thumbnail_url = nci.thumbnail_url OR (c.thumbnail_url IS NULL AND nci.thumbnail_url IS NULL));

-- Report migration statistics
DO $$
DECLARE
  entity_count int;
  variant_count int;
  component_count int;
  total_images int;
BEGIN
  SELECT COUNT(*) INTO entity_count FROM entities WHERE primary_image_id IS NOT NULL;
  SELECT COUNT(*) INTO variant_count FROM variants WHERE primary_image_id IS NOT NULL;
  SELECT COUNT(*) INTO component_count FROM components WHERE primary_image_id IS NOT NULL;
  SELECT COUNT(*) INTO total_images FROM images;

  RAISE NOTICE 'Image migration complete:';
  RAISE NOTICE '  - % entity images migrated', entity_count;
  RAISE NOTICE '  - % variant images migrated', variant_count;
  RAISE NOTICE '  - % component images migrated', component_count;
  RAISE NOTICE '  - % total images in images table', total_images;
END $$;
