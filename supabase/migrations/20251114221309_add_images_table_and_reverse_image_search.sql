-- Ensure required extensions are enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create standalone images table for unified image storage and embeddings
CREATE TABLE images (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  image_url text NOT NULL,
  thumbnail_url text,
  embedding vector(512),  -- CLIP embeddings (512 dimensions)
  source_url text,  -- Attribution/provenance
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Add primary image foreign keys to existing tables
ALTER TABLE entities ADD COLUMN primary_image_id uuid REFERENCES images(id) ON DELETE SET NULL;
ALTER TABLE variants ADD COLUMN primary_image_id uuid REFERENCES images(id) ON DELETE SET NULL;
ALTER TABLE components ADD COLUMN primary_image_id uuid REFERENCES images(id) ON DELETE SET NULL;

-- Create join tables for additional images
CREATE TABLE entity_additional_images (
  entity_id uuid REFERENCES entities(id) ON DELETE CASCADE,
  image_id uuid REFERENCES images(id) ON DELETE CASCADE,
  "order" int,
  PRIMARY KEY (entity_id, image_id)
);

CREATE TABLE variant_additional_images (
  variant_id uuid REFERENCES variants(id) ON DELETE CASCADE,
  image_id uuid REFERENCES images(id) ON DELETE CASCADE,
  "order" int,
  PRIMARY KEY (variant_id, image_id)
);

CREATE TABLE component_additional_images (
  component_id uuid REFERENCES components(id) ON DELETE CASCADE,
  image_id uuid REFERENCES images(id) ON DELETE CASCADE,
  "order" int,
  PRIMARY KEY (component_id, image_id)
);

-- Create indexes for fast lookups
CREATE INDEX idx_images_embedding ON images USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_entity_additional_images_entity ON entity_additional_images(entity_id);
CREATE INDEX idx_entity_additional_images_order ON entity_additional_images("order") WHERE "order" IS NOT NULL;
CREATE INDEX idx_variant_additional_images_variant ON variant_additional_images(variant_id);
CREATE INDEX idx_variant_additional_images_order ON variant_additional_images("order") WHERE "order" IS NOT NULL;
CREATE INDEX idx_component_additional_images_component ON component_additional_images(component_id);
CREATE INDEX idx_component_additional_images_order ON component_additional_images("order") WHERE "order" IS NOT NULL;

-- Create unified reverse image search function
-- Returns images ranked by similarity with their parent information
CREATE OR REPLACE FUNCTION image_search(
  query_embedding vector(512),
  result_limit int DEFAULT 20
)
RETURNS TABLE (
  image_id uuid,
  image_url text,
  thumbnail_url text,
  similarity float,
  parent_type text,
  parent_id uuid,
  parent_name text
)
LANGUAGE sql
STABLE
AS $$
  WITH image_similarities AS (
    -- Calculate similarity for all images with embeddings
    SELECT
      i.id,
      i.image_url,
      i.thumbnail_url,
      1 - (i.embedding <=> query_embedding) as similarity
    FROM images i
    WHERE i.embedding IS NOT NULL
    ORDER BY i.embedding <=> query_embedding
    LIMIT result_limit
  ),
  image_parents AS (
    -- Find all parent associations for matched images
    -- Primary images for entities
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'entity' as parent_type,
      e.id as parent_id,
      e.name as parent_name
    FROM image_similarities is_img
    JOIN entities e ON e.primary_image_id = is_img.id

    UNION ALL

    -- Additional images for entities
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'entity' as parent_type,
      e.id as parent_id,
      e.name as parent_name
    FROM image_similarities is_img
    JOIN entity_additional_images eai ON eai.image_id = is_img.id
    JOIN entities e ON e.id = eai.entity_id

    UNION ALL

    -- Primary images for variants
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'variant' as parent_type,
      v.id as parent_id,
      v.name as parent_name
    FROM image_similarities is_img
    JOIN variants v ON v.primary_image_id = is_img.id

    UNION ALL

    -- Additional images for variants
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'variant' as parent_type,
      v.id as parent_id,
      v.name as parent_name
    FROM image_similarities is_img
    JOIN variant_additional_images vai ON vai.image_id = is_img.id
    JOIN variants v ON v.id = vai.variant_id

    UNION ALL

    -- Primary images for components
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'component' as parent_type,
      c.id as parent_id,
      c.name as parent_name
    FROM image_similarities is_img
    JOIN components c ON c.primary_image_id = is_img.id

    UNION ALL

    -- Additional images for components
    SELECT
      is_img.id,
      is_img.image_url,
      is_img.thumbnail_url,
      is_img.similarity,
      'component' as parent_type,
      c.id as parent_id,
      c.name as parent_name
    FROM image_similarities is_img
    JOIN component_additional_images cai ON cai.image_id = is_img.id
    JOIN components c ON c.id = cai.component_id
  )
  -- Return all parent associations, ordered by similarity
  SELECT
    id as image_id,
    image_url,
    thumbnail_url,
    similarity,
    parent_type,
    parent_id,
    parent_name
  FROM image_parents
  ORDER BY similarity DESC;
$$;

-- Add helpful comment
COMMENT ON FUNCTION image_search IS 'Search for visually similar images across entities, variants, and components using CLIP embeddings. Returns ranked results with parent information.';
