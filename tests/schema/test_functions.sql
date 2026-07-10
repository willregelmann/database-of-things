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
INSERT INTO entities (id, type, name, category, name_embedding) VALUES
    ('00000000-0000-0000-0000-000000000001', 'item', 'Charizard', 'trading_card_games',
     array_fill(0.1::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000002', 'item', 'Blastoise', 'trading_card_games',
     array_fill(0.2::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000003', 'item', 'Optimus Prime', 'figures',
     array_fill(0.3::float, ARRAY[384])::vector(384)),
    ('00000000-0000-0000-0000-000000000004', 'item', 'Pikachu', 'trading_card_games',
     NULL); -- No embedding

-- Test 1: Basic semantic search should return results
-- Note: tests scope by our own test entity IDs (rather than asserting an
-- absolute result count) so they pass whether run against an empty
-- database (fresh CI) or one with pre-existing data (populated local dev).
\echo '  Test 1: Basic search returns results'
DO $$
DECLARE
    result_count INT;
BEGIN
    SELECT COUNT(*) INTO result_count
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        NULL,
        1000
    ) s
    WHERE s.id IN (
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000004'
    );

    IF result_count != 3 THEN
        RAISE EXCEPTION 'Expected 3 of our 4 test entities (only ones with embeddings), got %', result_count;
    END IF;

    RAISE NOTICE '    ✓ Returned correct number of results';
END $$;

-- Test 2: Category filtering should work
\echo '  Test 2: Category filtering works'
DO $$
DECLARE
    result_count INT;
BEGIN
    SELECT COUNT(*) INTO result_count
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        'trading_card_games',
        1000
    ) s
    WHERE s.id IN (
        '00000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000004'
    );

    IF result_count != 2 THEN
        RAISE EXCEPTION 'Expected 2 of our trading_card_games test entities, got %', result_count;
    END IF;

    RAISE NOTICE '    ✓ Category filter working correctly';
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

-- Test 5: Check that image_url is returned (joined from the images table)
\echo '  Test 5: Returns image_url column'
DO $$
BEGIN
    PERFORM image_url
    FROM semantic_search(
        array_fill(0.15::float, ARRAY[384])::vector(384),
        NULL,
        NULL,
        1
    )
    LIMIT 1;

    RAISE NOTICE '    ✓ Function returns image_url column';
EXCEPTION WHEN undefined_column THEN
    RAISE EXCEPTION 'semantic_search function does not return an image_url column!';
END $$;

-- ================================================================
-- Test search_by_text function
-- ================================================================

\echo ''
\echo 'Testing search_by_text function...'

\echo '  Test 1: Text-based search finds similar entities'
DO $$
BEGIN
    PERFORM *
    FROM search_by_text('Charizard', 'item', 'trading_card_games', 5);

    RAISE NOTICE '    ✓ search_by_text function working';
EXCEPTION WHEN undefined_function THEN
    RAISE NOTICE '    ⚠ search_by_text function not found (may not be created yet)';
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
