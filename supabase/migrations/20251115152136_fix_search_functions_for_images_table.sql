-- Fix semantic_search and search_by_text functions to remove image columns
-- (image_url and thumbnail_url no longer exist on entities table after images migration)

-- Drop existing functions first (can't change return type otherwise)
DROP FUNCTION IF EXISTS semantic_search(vector, text, integer);
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

-- Recreate semantic_search function
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
        e.attributes,
        1 - (e.name_embedding <=> query_embedding) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

-- Recreate search_by_text function
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
    attributes jsonb,
    similarity float
)
LANGUAGE sql
STABLE
AS $$
    -- Use trigram similarity to find the closest matching entity name
    -- then use its embedding as the search vector
    WITH closest_match AS (
        SELECT name_embedding
        FROM entities
        WHERE name_embedding IS NOT NULL
          AND similarity(name, query_text) > 0
        ORDER BY similarity(name, query_text) DESC
        LIMIT 1
    )
    SELECT
        e.id,
        e.name,
        e.type,
        e.year,
        e.country,
        e.language,
        e.attributes,
        1 - (e.name_embedding <=> cm.name_embedding) as similarity
    FROM entities e, closest_match cm
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> cm.name_embedding
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION semantic_search IS 'Performs vector similarity search on entity names. Returns entities ranked by semantic similarity to the query embedding. Use scripts/semantic-search for proper semantic search that handles synonyms and variations. Note: Image URLs must be fetched separately from images table.';

COMMENT ON FUNCTION search_by_text IS 'Performs text-based semantic search by finding the closest entity name match and using its embedding. WARNING: This fails for synonyms (e.g., "and" vs "&"). Use scripts/semantic-search instead for true semantic search. Note: Image URLs must be fetched separately from images table.';
