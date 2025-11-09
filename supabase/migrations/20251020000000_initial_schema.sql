-- ============================================
-- COLLECTIBLES DATABASE SCHEMA v1.0 (Minimal)
-- Pure graph: Just entities and relationships
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- CORE TABLES
-- ============================================

CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  -- Minimal standard fields
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  
  -- Optional universal metadata
  year INT,
  country CHAR(2),
  
  -- Everything else: external IDs, images, all attributes
  attributes JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE relationships (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  from_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  to_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  
  attributes JSONB DEFAULT '{}',
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(from_id, to_id, type)
);

-- ============================================
-- INDEXES
-- ============================================

-- Entity lookups
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_name_trgm ON entities USING gin(name gin_trgm_ops);

-- JSONB queries (covers external IDs, images, all attributes)
CREATE INDEX idx_entities_attributes ON entities USING gin(attributes jsonb_path_ops);

-- Full-text search
CREATE INDEX idx_entities_search ON entities USING gin(
  to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, ''))
);

-- Relationship traversal
CREATE INDEX idx_relationships_from_type ON relationships(from_id, type);
CREATE INDEX idx_relationships_to_type ON relationships(to_id, type);
CREATE INDEX idx_relationships_attributes ON relationships USING gin(attributes jsonb_path_ops);
