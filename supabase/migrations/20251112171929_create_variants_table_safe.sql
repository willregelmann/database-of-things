-- Create variants table (safe - checks if exists)
CREATE TABLE IF NOT EXISTS variants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  variant_of UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  image_url TEXT,
  thumbnail_url TEXT,
  attributes JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance (safe - checks if exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_variants_variant_of') THEN
        CREATE INDEX idx_variants_variant_of ON variants(variant_of);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_variants_attributes') THEN
        CREATE INDEX idx_variants_attributes ON variants USING GIN(attributes);
    END IF;
END$$;

-- Add PostgreSQL function for GraphQL computed field
CREATE OR REPLACE FUNCTION entity_variants(entity_row entities)
RETURNS SETOF variants AS $$
  SELECT * FROM variants WHERE variant_of = entity_row.id
$$ LANGUAGE SQL STABLE;

-- Tell PostgREST/GraphQL about the relationship
COMMENT ON FUNCTION entity_variants IS
  '@graphql({"totalCount": {"enabled": true}})';
