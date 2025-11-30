-- ============================================
-- ADD CATEGORY FILTER TO SEARCH FUNCTIONS
-- ============================================
-- Adds optional category_filter parameter to semantic_search and
-- search_by_text functions, allowing searches to be scoped by domain
-- (trading_card_games, figures, comics, video_games, buildables).
-- ============================================

-- Drop existing functions (signature change requires drop)
-- Note: PostgreSQL stores vector(384) as just 'vector' in pg_proc
DROP FUNCTION IF EXISTS semantic_search(vector, text, integer);
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

-- ============================================
-- SEMANTIC_SEARCH: Vector-based search with category filter
-- ============================================
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    entity_type_filter text DEFAULT NULL,
    category_filter text DEFAULT NULL,
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
      AND (category_filter IS NULL OR e.category::text = category_filter)
    ORDER BY e.name_embedding <=> query_embedding
    LIMIT result_limit;
$$;

COMMENT ON FUNCTION semantic_search(vector, text, text, integer) IS 'Vector similarity search with optional type and category filters. Returns entities with similarity scores and image URLs. Access via MCP tools or SQL (not GraphQL).';

GRANT EXECUTE ON FUNCTION semantic_search(vector, text, text, integer) TO anon, authenticated;

-- ============================================
-- SEARCH_BY_TEXT: Text-based search with category filter
-- ============================================
CREATE OR REPLACE FUNCTION search_by_text(
    query_text text,
    entity_type_filter text DEFAULT NULL,
    category_filter text DEFAULT NULL,
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
          AND (category_filter IS NULL OR entities.category::text = category_filter)
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
      AND (category_filter IS NULL OR e.category::text = category_filter)
    ORDER BY e.name_embedding <=> r.name_embedding
    LIMIT result_limit;
END;
$$;

COMMENT ON FUNCTION search_by_text(text, text, text, integer) IS 'Text-based semantic search with optional type and category filters. WARNING: Fails for synonyms - use MCP search_collectibles for true semantic search.';

GRANT EXECUTE ON FUNCTION search_by_text(text, text, text, integer) TO anon, authenticated;
