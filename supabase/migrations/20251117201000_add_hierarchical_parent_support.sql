-- Add hierarchical parent relationship support to bulk import
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
  v_parent_id uuid;
  v_parent_external_ids jsonb;
  v_parent_key text;
  v_parent_value text;
  v_items_without_parent jsonb[];
  v_items_with_parent jsonb[];
BEGIN
  v_start_time := clock_timestamp();

  -- Validate collection exists
  IF NOT EXISTS (SELECT 1 FROM entities WHERE id = p_collection_id) THEN
    RAISE EXCEPTION 'Collection with id % not found', p_collection_id;
  END IF;

  -- Separate items into two groups: with and without parent
  SELECT 
    ARRAY_AGG(item) FILTER (WHERE NOT (item ? 'parent')),
    ARRAY_AGG(item) FILTER (WHERE item ? 'parent')
  INTO v_items_without_parent, v_items_with_parent
  FROM jsonb_array_elements(p_items) AS item;

  -- PASS 1: Process items WITHOUT parent (top-level items)
  IF v_items_without_parent IS NOT NULL THEN
    FOR v_item IN SELECT * FROM unnest(v_items_without_parent)
    LOOP
      BEGIN
        -- Map type to entity_type enum
        v_entity_type := CASE
          WHEN LOWER(v_item->>'type') IN ('collection', 'set', 'series') THEN 'collection'::entity_type
          ELSE 'item'::entity_type
        END;

        -- Extract external_id for deduplication
        v_external_id_key := NULL;
        v_external_id_value := NULL;

        IF v_item ? 'external_ids' AND jsonb_typeof(v_item->'external_ids') = 'object' THEN
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
          IF p_skip_duplicates THEN
            v_skipped_count := v_skipped_count + 1;
            
            -- Ensure relationship to root exists
            INSERT INTO relationships (from_id, to_id, "order")
            VALUES (p_collection_id, v_existing_id, (v_item->>'order')::int)
            ON CONFLICT (from_id, to_id) DO NOTHING;
          END IF;
        ELSE
          -- Create new entity
          INSERT INTO entities (
            name, type, category, year, country, language, source_url, external_ids, attributes
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

          -- Create relationship to root collection
          INSERT INTO relationships (from_id, to_id, "order")
          VALUES (p_collection_id, v_new_id, (v_item->>'order')::int);
        END IF;

      EXCEPTION WHEN OTHERS THEN
        v_errors := v_errors || jsonb_build_object(
          'item', v_item->>'name',
          'error', SQLERRM
        );
      END;
    END LOOP;
  END IF;

  -- PASS 2: Process items WITH parent (child items)
  IF v_items_with_parent IS NOT NULL THEN
    FOR v_item IN SELECT * FROM unnest(v_items_with_parent)
    LOOP
      BEGIN
        -- Map type to entity_type enum
        v_entity_type := CASE
          WHEN LOWER(v_item->>'type') IN ('collection', 'set', 'series') THEN 'collection'::entity_type
          ELSE 'item'::entity_type
        END;

        -- Extract external_id for deduplication
        v_external_id_key := NULL;
        v_external_id_value := NULL;

        IF v_item ? 'external_ids' AND jsonb_typeof(v_item->'external_ids') = 'object' THEN
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

        -- Resolve parent by external_ids
        v_parent_id := NULL;
        IF v_item ? 'parent' AND v_item->'parent' ? 'external_ids' THEN
          v_parent_external_ids := v_item->'parent'->'external_ids';
          
          -- Try each external_id key/value pair until we find a match
          FOR v_parent_key, v_parent_value IN 
            SELECT key, value FROM jsonb_each_text(v_parent_external_ids)
          LOOP
            SELECT id INTO v_parent_id
            FROM entities
            WHERE external_ids @> jsonb_build_object(v_parent_key, v_parent_value)
            LIMIT 1;
            
            EXIT WHEN v_parent_id IS NOT NULL;
          END LOOP;
        END IF;

        -- Default to root collection if parent not found
        IF v_parent_id IS NULL THEN
          v_parent_id := p_collection_id;
        END IF;

        IF v_existing_id IS NOT NULL THEN
          IF p_skip_duplicates THEN
            v_skipped_count := v_skipped_count + 1;
            
            -- Ensure relationship to parent exists
            INSERT INTO relationships (from_id, to_id, "order")
            VALUES (v_parent_id, v_existing_id, (v_item->'relationship'->>'order')::int)
            ON CONFLICT (from_id, to_id) DO NOTHING;
          END IF;
        ELSE
          -- Create new entity
          INSERT INTO entities (
            name, type, category, year, country, language, source_url, external_ids, attributes
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

          -- Create relationship to resolved parent
          INSERT INTO relationships (from_id, to_id, "order")
          VALUES (v_parent_id, v_new_id, (v_item->'relationship'->>'order')::int);
        END IF;

      EXCEPTION WHEN OTHERS THEN
        v_errors := v_errors || jsonb_build_object(
          'item', v_item->>'name',
          'error', SQLERRM,
          'parent_resolved', v_parent_id IS NOT NULL
        );
      END;
    END LOOP;
  END IF;

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
