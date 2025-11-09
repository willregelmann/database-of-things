-- ================================================================
-- Migration: Fix semantic_search and search_by_text functions
-- ================================================================
-- These functions were referencing the deleted 'image_key' column.
-- Update them to use 'image_url' and 'thumbnail_url' instead.

-- ================================================================
-- Fix semantic_search function
-- ================================================================

-- Drop existing functions first (needed when changing return type)
DROP FUNCTION IF EXISTS semantic_search(vector, text, integer);
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    year integer,
    country char(2),
    language char(2),
    image_url text,
    thumbnail_url text,
    attributes jsonb,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.id,
        e.name,
        e.type,
        e.year,
        e.country,
        e.language,
        e.image_url,
        e.thumbnail_url,
        e.attributes,
        1 - (e.name_embedding <=> query_embedding) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION semantic_search IS
    'Performs vector similarity search on entity names. Returns entities ranked by semantic similarity to the query embedding.';

-- ================================================================
-- Fix search_by_text function (if it exists)
-- ================================================================

CREATE OR REPLACE FUNCTION search_by_text(
    query_text text,
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    year integer,
    country char(2),
    language char(2),
    image_url text,
    thumbnail_url text,
    attributes jsonb,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    WITH reference_entity AS (
        -- Find an entity matching the query text to use as reference
        SELECT name_embedding
        FROM entities
        WHERE name ILIKE '%' || query_text || '%'
          AND name_embedding IS NOT NULL
          AND (entity_type_filter IS NULL OR type = entity_type_filter)
        LIMIT 1
    )
    SELECT
        e.id,
        e.name,
        e.type,
        e.year,
        e.country,
        e.language,
        e.image_url,
        e.thumbnail_url,
        e.attributes,
        1 - (e.name_embedding <=> (SELECT name_embedding FROM reference_entity)) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
      AND EXISTS (SELECT 1 FROM reference_entity)
    ORDER BY e.name_embedding <=> (SELECT name_embedding FROM reference_entity)
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION search_by_text IS
    'Text-based semantic search. Finds an entity matching the query text and returns semantically similar entities.';

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION semantic_search TO anon, authenticated;
GRANT EXECUTE ON FUNCTION search_by_text TO anon, authenticated;
