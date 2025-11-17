-- Fix bulk import to map common type names to entity_type enum
CREATE OR REPLACE FUNCTION import_curator_batch(
  p_collection_id uuid,
  p_items jsonb,
  p_skip_duplicates boolean DEFAULT true,
  p_update_existing boolean DEFAULT false
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  v_result jsonb;
  v_created_count int := 0;
  v_updated_count int := 0;
  v_skipped_count int := 0;
  v_created_ids uuid[] := ARRAY[]::uuid[];
  v_updated_ids uuid[] := ARRAY[]::uuid[];
  v_errors jsonb := '[]'::jsonb;
  v_start_time timestamptz;
  v_item jsonb;
  v_external_id_key text;
  v_external_id_value text;
  v_existing_id uuid;
  v_new_id uuid;
  v_entity_type entity_type;
BEGIN
  v_start_time := clock_timestamp();

  -- Validate collection exists
  IF NOT EXISTS (SELECT 1 FROM entities WHERE id = p_collection_id) THEN
    RAISE EXCEPTION 'Collection with id % not found', p_collection_id;
  END IF;

  -- Process each item
  FOR v_item IN SELECT * FROM jsonb_array_elements(p_items)
  LOOP
    BEGIN
      -- Map type to entity_type enum
      -- card, comic, figure, video_game, etc. → item
      -- collection, set, series → collection
      v_entity_type := CASE
        WHEN LOWER(v_item->>'type') IN ('collection', 'set', 'series') THEN 'collection'::entity_type
        ELSE 'item'::entity_type
      END;

      -- Extract external_id for deduplication
      v_external_id_key := NULL;
      v_external_id_value := NULL;

      IF v_item ? 'external_ids' AND jsonb_typeof(v_item->'external_ids') = 'object' THEN
        -- Get first external_id key/value pair
        SELECT key, value INTO v_external_id_key, v_external_id_value
        FROM jsonb_each_text(v_item->'external_ids')
        LIMIT 1;
      END IF;

      -- Check if entity already exists
      v_existing_id := NULL;
      IF v_external_id_key IS NOT NULL AND v_external_id_value IS NOT NULL THEN
        SELECT id INTO v_existing_id
        FROM entities
        WHERE external_ids @> jsonb_build_object(v_external_id_key, v_external_id_value)
        LIMIT 1;
      END IF;

      IF v_existing_id IS NOT NULL THEN
        -- Entity exists
        IF p_update_existing THEN
          -- Update existing entity
          UPDATE entities
          SET
            name = COALESCE((v_item->>'name')::text, name),
            year = COALESCE((v_item->>'year')::int, year),
            country = COALESCE((v_item->>'country')::char(2), country),
            language = COALESCE((v_item->>'language')::char(2), language),
            source_url = COALESCE((v_item->>'source_url')::text, source_url),
            category = COALESCE((v_item->>'category')::category_type, category),
            external_ids = COALESCE((v_item->'external_ids')::jsonb, external_ids),
            attributes = COALESCE((v_item->'attributes')::jsonb, attributes),
            updated_at = NOW()
          WHERE id = v_existing_id;

          v_updated_count := v_updated_count + 1;
          v_updated_ids := array_append(v_updated_ids, v_existing_id);

          -- Ensure relationship exists
          INSERT INTO relationships (from_id, to_id, "order")
          VALUES (
            p_collection_id,
            v_existing_id,
            (v_item->>'order')::int
          )
          ON CONFLICT (from_id, to_id) DO UPDATE
          SET "order" = COALESCE(EXCLUDED."order", relationships."order");

        ELSIF p_skip_duplicates THEN
          -- Skip duplicate
          v_skipped_count := v_skipped_count + 1;
        ELSE
          -- Error on duplicate
          v_errors := v_errors || jsonb_build_object(
            'item', v_item->>'name',
            'error', 'Duplicate entity with external_id: ' || v_external_id_key || '=' || v_external_id_value
          );
        END IF;
      ELSE
        -- Create new entity
        INSERT INTO entities (
          name,
          type,
          category,
          year,
          country,
          language,
          source_url,
          external_ids,
          attributes
        )
        VALUES (
          (v_item->>'name')::text,
          v_entity_type,
          (v_item->>'category')::category_type,
          (v_item->>'year')::int,
          (v_item->>'country')::char(2),
          (v_item->>'language')::char(2),
          (v_item->>'source_url')::text,
          COALESCE((v_item->'external_ids')::jsonb, '{}'::jsonb),
          COALESCE((v_item->'attributes')::jsonb, '{}'::jsonb)
        )
        RETURNING id INTO v_new_id;

        v_created_count := v_created_count + 1;
        v_created_ids := array_append(v_created_ids, v_new_id);

        -- Create relationship to collection
        INSERT INTO relationships (from_id, to_id, "order")
        VALUES (
          p_collection_id,
          v_new_id,
          (v_item->>'order')::int
        );
      END IF;

    EXCEPTION WHEN OTHERS THEN
      -- Capture individual item errors
      v_errors := v_errors || jsonb_build_object(
        'item', v_item->>'name',
        'error', SQLERRM
      );
    END;
  END LOOP;

  -- Return summary
  v_result := jsonb_build_object(
    'success', true,
    'summary', jsonb_build_object(
      'total', jsonb_array_length(p_items),
      'created', v_created_count,
      'updated', v_updated_count,
      'skipped', v_skipped_count,
      'errors', jsonb_array_length(v_errors)
    ),
    'created_entity_ids', to_jsonb(v_created_ids),
    'updated_entity_ids', to_jsonb(v_updated_ids),
    'errors', v_errors,
    'execution_time_ms', EXTRACT(MILLISECOND FROM clock_timestamp() - v_start_time)
  );

  RETURN v_result;
END;
$$;
