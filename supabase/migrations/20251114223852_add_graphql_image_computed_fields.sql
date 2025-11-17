-- Add GraphQL computed fields for easy image access from entities, variants, and components
-- These functions enable GraphQL queries like: entity { primary_image { ... }, additional_images { ... } }

-- Computed field: Get primary image for an entity
CREATE OR REPLACE FUNCTION entity_primary_image(entity_row entities)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM images
  WHERE id = entity_row.primary_image_id;
$$;

-- Computed field: Get additional images for an entity
CREATE OR REPLACE FUNCTION entity_additional_images(entity_row entities)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT i.*
  FROM images i
  JOIN entity_additional_images eai ON eai.image_id = i.id
  WHERE eai.entity_id = entity_row.id
  ORDER BY eai."order" NULLS LAST, i.created_at;
$$;

-- Computed field: Get primary image for a variant
CREATE OR REPLACE FUNCTION variant_primary_image(variant_row variants)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM images
  WHERE id = variant_row.primary_image_id;
$$;

-- Computed field: Get additional images for a variant
CREATE OR REPLACE FUNCTION variant_additional_images(variant_row variants)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT i.*
  FROM images i
  JOIN variant_additional_images vai ON vai.image_id = i.id
  WHERE vai.variant_id = variant_row.id
  ORDER BY vai."order" NULLS LAST, i.created_at;
$$;

-- Computed field: Get primary image for a component
CREATE OR REPLACE FUNCTION component_primary_image(component_row components)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT * FROM images
  WHERE id = component_row.primary_image_id;
$$;

-- Computed field: Get additional images for a component
CREATE OR REPLACE FUNCTION component_additional_images(component_row components)
RETURNS SETOF images
LANGUAGE sql
STABLE
AS $$
  SELECT i.*
  FROM images i
  JOIN component_additional_images cai ON cai.image_id = i.id
  WHERE cai.component_id = component_row.id
  ORDER BY cai."order" NULLS LAST, i.created_at;
$$;

-- Add helpful comments
COMMENT ON FUNCTION entity_primary_image IS 'GraphQL computed field: Returns primary image for an entity';
COMMENT ON FUNCTION entity_additional_images IS 'GraphQL computed field: Returns additional images for an entity';
COMMENT ON FUNCTION variant_primary_image IS 'GraphQL computed field: Returns primary image for a variant';
COMMENT ON FUNCTION variant_additional_images IS 'GraphQL computed field: Returns additional images for a variant';
COMMENT ON FUNCTION component_primary_image IS 'GraphQL computed field: Returns primary image for a component';
COMMENT ON FUNCTION component_additional_images IS 'GraphQL computed field: Returns additional images for a component';
