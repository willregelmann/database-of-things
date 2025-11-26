-- ============================================
-- ADD IMAGE URLs TO SEARCH FUNCTIONS
-- ============================================
-- Joins the images table to include image_url and thumbnail_url
-- directly in search results, avoiding extra round trips.
--
-- IMPORTANT: These functions are NOT exposed via GraphQL due to
-- pg_graphql limitations (RETURNS TABLE and vector types unsupported).
-- Use via REST API: POST /rest/v1/rpc/search_by_text
-- ============================================

-- Drop existing functions (need to drop due to signature change)
DROP FUNCTION IF EXISTS semantic_search(vector(384), entity_type, integer);
DROP FUNCTION IF EXISTS semantic_search(vector(384), text, integer);
DROP FUNCTION IF EXISTS search_by_text(text, entity_type, integer);
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

-- ============================================
-- SEMANTIC_SEARCH: Vector-based search with image URLs
-- ============================================
-- Access via: MCP tools (search_collectibles) or direct SQL
-- NOT available via GraphQL (vector type not supported)
-- ============================================
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    category text,
    year integer,
    country char(2),
    language char(2),
    source_url text,
    external_ids jsonb,
    attributes jsonb,
    similarity float,
    image_url text,
    thumbnail_url text
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        e.id,
        e.name,
        e.type::text,
        e.category::text,
        e.year,
        e.country,
        e.language,
        e.source_url,
        e.external_ids,
        e.attributes,
        (1 - (e.name_embedding <=> query_embedding))::float as similarity,
        i.image_url,
        i.thumbnail_url
    FROM entities e
    LEFT JOIN images i ON e.primary_image_id = i.id
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type::text = entity_type_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION semantic_search IS 'Vector similarity search. Returns entities with similarity scores and image URLs. Access via MCP tools or SQL (not GraphQL).';

GRANT EXECUTE ON FUNCTION semantic_search TO anon, authenticated;

-- ============================================
-- SEARCH_BY_TEXT: Text-based search with image URLs
-- ============================================
-- Access via: REST API (POST /rest/v1/rpc/search_by_text)
-- NOT available via GraphQL (RETURNS TABLE not supported)
--
-- NOTE: Uses trigram similarity to find a reference entity, then
-- semantic search from that entity's embedding. Fails for synonyms.
-- For true semantic search, use MCP search_collectibles tool.
-- ============================================
CREATE OR REPLACE FUNCTION search_by_text(
    query_text text,
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE (
    id uuid,
    name text,
    type text,
    category text,
    year integer,
    country char(2),
    language char(2),
    source_url text,
    external_ids jsonb,
    attributes jsonb,
    similarity float,
    image_url text,
    thumbnail_url text
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
    RETURN QUERY
    WITH ref AS (
        SELECT name_embedding
        FROM entities
        WHERE name_embedding IS NOT NULL
          AND (entity_type_filter IS NULL OR entities.type::text = entity_type_filter)
        ORDER BY similarity(entities.name, query_text) DESC
        LIMIT 1
    )
    SELECT
        e.id,
        e.name,
        e.type::text,
        e.category::text,
        e.year,
        e.country,
        e.language,
        e.source_url,
        e.external_ids,
        e.attributes,
        (1 - (e.name_embedding <=> r.name_embedding))::float,
        i.image_url,
        i.thumbnail_url
    FROM entities e
    LEFT JOIN images i ON e.primary_image_id = i.id
    CROSS JOIN ref r
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type::text = entity_type_filter)
    ORDER BY e.name_embedding <=> r.name_embedding
    LIMIT result_limit;
END;
$$;

COMMENT ON FUNCTION search_by_text IS 'Text-based semantic search via REST API. Returns similarity scores and image URLs. WARNING: Fails for synonyms - use MCP search_collectibles for true semantic search.';

GRANT EXECUTE ON FUNCTION search_by_text TO anon, authenticated;
