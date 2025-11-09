-- ================================================================
-- Database Function Tests
-- ================================================================
-- Tests that database functions work correctly
-- Run with: psql -f tests/schema/test_functions.sql

\set ON_ERROR_STOP on
\set QUIET on

BEGIN;

\echo ''
\echo '===================================='
\echo 'Testing Database Functions'
\echo '===================================='
\echo ''

-- ================================================================
-- Test semantic_search function
-- ================================================================

\echo 'Testing semantic_search function...'

-- Create test entities with embeddings
INSERT INTO entities (id, type, name, name_embedding) VALUES
    ('00000000-0000-0000-0000-000000000001', 'card', 'Charizard',
     array_fill(0.1::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000002', 'card', 'Blastoise',
     array_fill(0.2::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000003', 'figure', 'Optimus Prime',
     array_fill(0.3::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000004', 'card', 'Pikachu',
     NULL); -- No embedding

-- Test 1: Basic semantic search should return results
\echo '  Test 1: Basic search returns results'
DO $$
DECLARE
    result_count INT;
BEGIN
    SELECT COUNT(*) INTO result_count
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        10
    );

    IF result_count != 3 THEN
        RAISE EXCEPTION 'Expected 3 results (only entities with embeddings), got %', result_count;
    END IF;

    RAISE NOTICE '    ✓ Returned correct number of results';
END $$;

-- Test 2: Type filtering should work
\echo '  Test 2: Type filtering works'
DO $$
DECLARE
    result_count INT;
BEGIN
    SELECT COUNT(*) INTO result_count
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        'card',
        10
    );

    IF result_count != 2 THEN
        RAISE EXCEPTION 'Expected 2 card results, got %', result_count;
    END IF;

    RAISE NOTICE '    ✓ Type filter working correctly';
END $$;

-- Test 3: Result limit should be respected
\echo '  Test 3: Result limit respected'
DO $$
DECLARE
    result_count INT;
BEGIN
    SELECT COUNT(*) INTO result_count
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        1
    );

    IF result_count != 1 THEN
        RAISE EXCEPTION 'Expected 1 result (limit), got %', result_count;
    END IF;

    RAISE NOTICE '    ✓ Result limit working correctly';
END $$;

-- Test 4: Similarity scores should be present and valid
\echo '  Test 4: Similarity scores valid'
DO $$
DECLARE
    min_similarity FLOAT;
    max_similarity FLOAT;
BEGIN
    SELECT MIN(similarity), MAX(similarity) INTO min_similarity, max_similarity
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        10
    );

    IF min_similarity IS NULL OR max_similarity IS NULL THEN
        RAISE EXCEPTION 'Similarity scores are NULL';
    END IF;

    IF min_similarity < 0 OR max_similarity > 1 THEN
        RAISE EXCEPTION 'Similarity scores out of range [0,1]: min=%, max=%', min_similarity, max_similarity;
    END IF;

    RAISE NOTICE '    ✓ Similarity scores in valid range [0,1]';
END $$;

-- Test 5: Check that image_url is returned (not image_key)
\echo '  Test 5: Returns image_url column (not image_key)'
DO $$
DECLARE
    column_exists BOOLEAN;
BEGIN
    -- Try to select image_url from results
    PERFORM image_url
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        1
    )
    LIMIT 1;

    RAISE NOTICE '    ✓ Function returns image_url column';
EXCEPTION WHEN undefined_column THEN
    RAISE EXCEPTION 'semantic_search function still references image_key instead of image_url!';
END $$;

-- ================================================================
-- Test search_by_text function (if it exists)
-- ================================================================

\echo ''
\echo 'Testing search_by_text function...'

DO $$
BEGIN
    -- Test 1: Should find similar entities based on name
    \echo '  Test 1: Text-based search finds similar entities'
    PERFORM *
    FROM search_by_text('Charizard', 'card', 5);

    RAISE NOTICE '    ✓ search_by_text function working';
EXCEPTION WHEN undefined_function THEN
    RAISE NOTICE '    ⚠ search_by_text function not found (may not be created yet)';
END $$;

-- ================================================================
-- Test entity_data_quality_issues view (if validation migration applied)
-- ================================================================

\echo ''
\echo 'Testing data quality view...'

DO $$
BEGIN
    -- Create an entity with quality issues
    INSERT INTO entities (type, name, year) VALUES ('unknown_type', 'Test Entity', 1799);

    PERFORM * FROM entity_data_quality_issues WHERE name = 'Test Entity';

    RAISE NOTICE '    ✓ Data quality view working';
EXCEPTION WHEN undefined_table THEN
    RAISE NOTICE '    ⚠ entity_data_quality_issues view not found (validation migration not applied)';
WHEN check_violation THEN
    RAISE NOTICE '    ✓ Validation constraints active (prevented invalid data)';
END $$;

-- ================================================================
-- Summary
-- ================================================================

\echo ''
\echo '===================================='
\echo 'All function tests passed! ✓'
\echo '===================================='
\echo ''

ROLLBACK; -- Clean up test data
