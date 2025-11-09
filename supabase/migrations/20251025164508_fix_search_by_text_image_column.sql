-- Fix search_by_text function to use image_url instead of image_key
-- The entities table uses image_url, not image_key

-- Need to drop first because we're changing the return type
DROP FUNCTION IF EXISTS search_by_text(text, text, integer);

CREATE OR REPLACE FUNCTION public.search_by_text(query_text text, entity_type_filter text DEFAULT NULL::text, result_limit integer DEFAULT 20)
 RETURNS TABLE(id uuid, name text, type text, year integer, country character, language character, image_url text, attributes jsonb, similarity double precision)
 LANGUAGE sql
 STABLE
AS $function$
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
        e.image_url,
        e.attributes,
        1 - (e.name_embedding <=> cm.name_embedding) as similarity
    FROM entities e, closest_match cm
    WHERE e.name_embedding IS NOT NULL
      AND (entity_type_filter IS NULL OR e.type = entity_type_filter)
    ORDER BY e.name_embedding <=> cm.name_embedding
    LIMIT result_limit;
$function$;
