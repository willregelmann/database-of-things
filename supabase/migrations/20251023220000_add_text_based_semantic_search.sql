-- ================================================================
-- Migration: Add text-based semantic search wrapper
-- ================================================================
-- Creates a user-friendly PostgreSQL function that accepts text
-- queries and automatically generates embeddings for semantic search.
--
-- NOTE: This function requires embeddings to be pre-generated via
-- the Python script. It searches for the closest match in existing
-- embeddings rather than generating new ones on-the-fly.
--
-- Usage via GraphQL:
--   query {
--     search_by_text(
--       args: {
--         query_text: "fire dragon pokemon"
--         entity_type_filter: "trading_card"
--         result_limit: 20
--       }
--     ) {
--       id
--       name
--       type
--       similarity
--     }
--   }
-- ================================================================

-- Create a text-based semantic search function
-- This uses a proxy approach: find the entity whose name is most similar
-- to the query text, then use its embedding to search for similar entities
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
    image_key text,
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
        e.image_key,
        e.attributes,
        1 - (e.name_embedding <=> cm.name_embedding) as similarity
    FROM entities e, closest_match cm
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> cm.name_embedding
    LIMIT result_limit;
$$;

-- Add comment for documentation
COMMENT ON FUNCTION search_by_text IS 'Performs text-based semantic search by finding the closest entity name match and using its embedding. Accepts plain text queries.';

-- Grant execute permission to authenticated and anonymous users
GRANT EXECUTE ON FUNCTION search_by_text TO anon, authenticated;
