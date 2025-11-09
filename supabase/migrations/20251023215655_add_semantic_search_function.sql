-- ================================================================
-- Migration: Add semantic search function for GraphQL
-- ================================================================
-- Creates a PostgreSQL function that performs vector similarity
-- search and can be queried via Supabase GraphQL API.
--
-- Usage via GraphQL:
--   query {
--     semantic_search(
--       args: {
--         query_embedding: "[0.123, 0.456, ...]"
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

-- Create the semantic search function
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
    image_key text,
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
        e.image_key,
        e.attributes,
        1 - (e.name_embedding <=> query_embedding) as similarity
    FROM entities e
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

-- Add comment for documentation
COMMENT ON FUNCTION semantic_search IS 'Performs vector similarity search on entity names. Returns entities ranked by semantic similarity to the query embedding.';

-- Grant execute permission to authenticated and anonymous users
GRANT EXECUTE ON FUNCTION semantic_search TO anon, authenticated;
