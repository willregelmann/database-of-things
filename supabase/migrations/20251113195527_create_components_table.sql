-- Enable uuid-ossp extension (idempotent)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create components table
CREATE TABLE components (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  component_of UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  quantity INTEGER DEFAULT 1,
  "order" INTEGER,
  image_url TEXT,
  thumbnail_url TEXT,
  attributes JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_components_component_of ON components(component_of);
CREATE INDEX idx_components_order ON components("order") WHERE "order" IS NOT NULL;
CREATE INDEX idx_components_attributes ON components USING GIN(attributes);

-- Add PostgreSQL function for GraphQL computed field
CREATE OR REPLACE FUNCTION entity_components(entity_row entities)
RETURNS SETOF components AS $$
  SELECT * FROM components
  WHERE component_of = entity_row.id
  ORDER BY COALESCE("order", 999999), name
$$ LANGUAGE SQL STABLE;

-- Tell PostgREST/GraphQL about the relationship
COMMENT ON FUNCTION entity_components IS
  '@graphql({"totalCount": {"enabled": true}})';
