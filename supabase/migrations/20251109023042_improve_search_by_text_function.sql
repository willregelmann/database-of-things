-- Improve search_by_text to use plpgsql with proper parameter scoping
--
-- Previous version used LANGUAGE sql which had textual parameter substitution issues.
-- This version uses LANGUAGE plpgsql with proper runtime parameter binding.
--
-- The function works by:
-- 1. Finding a reference entity using trigram similarity (fuzzy text matching)
-- 2. Using that entity's embedding to find semantically similar entities
--
-- Note: Works best when query text reasonably matches entity names (55%+ similarity)
-- Example: "journey into mystery"  works, "journey mystery" L too low similarity

CREATE OR REPLACE FUNCTION public.search_by_text(
    query_text text,
    entity_type_filter text DEFAULT NULL,
    result_limit integer DEFAULT 20
)
RETURNS TABLE(
    id uuid,
    name text,
    type text,
    year integer,
    country character(2),
    language character(2),
    image_url text,
    thumbnail_url text,
    attributes jsonb,
    similarity double precision
)
LANGUAGE plpgsql
STABLE
AS $function$
BEGIN
    RETURN QUERY
    WITH ref AS (
        SELECT name_embedding
        FROM entities
        WHERE name_embedding IS NOT NULL
          AND ($2 IS NULL OR type = $2)
        ORDER BY similarity(name, $1) DESC
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
        (1 - (e.name_embedding <=> r.name_embedding))::double precision
    FROM entities e
    CROSS JOIN ref r
    WHERE e.name_embedding IS NOT NULL
      AND ($2 IS NULL OR e.type = $2)
    ORDER BY e.name_embedding <=> r.name_embedding
    LIMIT $3;
END;
$function$;

COMMENT ON FUNCTION search_by_text IS 'Text-based semantic search using trigram similarity to find reference entity, then vector similarity for results. Best with queries matching entity names.';
