-- Create a view that includes computed image URLs
-- This exposes full image URLs in GraphQL while keeping the flexible image_key storage

CREATE OR REPLACE VIEW entities_with_urls AS
SELECT
  id,
  type,
  name,
  year,
  country,
  image_key,
  get_image_url(image_key) AS image_url,  -- Computed full URL
  attributes,
  external_ids,
  created_at,
  updated_at
FROM entities;

-- Add comment to explain the view
COMMENT ON VIEW entities_with_urls IS 'Entities with computed image_url field. Use this view in GraphQL to get full image URLs instead of storage keys.';

-- Grant access to the view (Supabase uses anon and authenticated roles)
GRANT SELECT ON entities_with_urls TO anon, authenticated;
