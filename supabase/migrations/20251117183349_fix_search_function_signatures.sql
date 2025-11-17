-- ============================================
-- FIX SEARCH FUNCTION SIGNATURES
-- ============================================
-- Problems fixed:
-- 1. Use entity_type enum instead of text for type filtering
-- 2. Ensure functions return only columns that exist
-- 3. Remove references to deleted image_url/thumbnail_url columns
-- ============================================

-- Drop existing functions
DROP FUNCTION IF EXISTS semantic_search(vector(384), text, integer);
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

-- ============================================
-- SEMANTIC_SEARCH: Vector-based search with proper entity_type enum
-- ============================================
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    entity_type_filter entity_type DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type entity_type,
    category category_type,
    year integer,
    country char(2),
    language char(2),
    source_url text,
    external_ids jsonb,
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
        e.category,
        e.year,
        e.country,
        e.language,
        e.source_url,
        e.external_ids,
        e.attributes,
        (1 - (e.name_embedding <=> query_embedding))::float as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION semantic_search IS 'Performs vector similarity search on entity names using cosine distance. Returns entities ranked by semantic similarity. Use entity_primary_image() computed field to fetch images via GraphQL.';

GRANT EXECUTE ON FUNCTION semantic_search TO anon, authenticated;

-- ============================================
-- SEARCH_BY_TEXT: Text-based search with proper entity_type enum
-- ============================================
-- NOTE: This function has fundamental limitations (see CLAUDE.md)
-- It finds a reference entity by name similarity, then uses that entity's
-- embedding. This fails for synonyms and variations.
-- Consider using scripts/semantic-search CLI tool instead.
-- ============================================
CREATE OR REPLACE FUNCTION search_by_text(
    query_text text,
    entity_type_filter entity_type DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type entity_type,
    category category_type,
    year integer,
    country char(2),
    language char(2),
    source_url text,
    external_ids jsonb,
    attributes jsonb,
    similarity float
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH ref AS (
        -- Find reference entity with most similar name (trigram)
        SELECT name_embedding
        FROM entities
        WHERE name_embedding IS NOT NULL
          AND (entity_type_filter IS NULL OR entities.type = entity_type_filter)
        ORDER BY similarity(entities.name, query_text) DESC
        LIMIT 1
    )
    SELECT
        e.id,
        e.name,
        e.type,
        e.category,
        e.year,
        e.country,
        e.language,
        e.source_url,
        e.external_ids,
        e.attributes,
        (1 - (e.name_embedding <=> r.name_embedding))::float as similarity
    FROM entities e
    CROSS JOIN ref r
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> r.name_embedding
    LIMIT result_limit;
END;
$$;

COMMENT ON FUNCTION search_by_text IS 'Text-based semantic search using trigram similarity to find reference entity. WARNING: Fails for synonyms ("and" vs "&"). Use scripts/semantic-search CLI tool for true semantic search. Use entity_primary_image() computed field to fetch images via GraphQL.';

GRANT EXECUTE ON FUNCTION search_by_text TO anon, authenticated;
