-- ================================================================
-- Schema Constraint Tests
-- ================================================================
-- Tests that database constraints are properly enforced
-- Run with: psql -f tests/schema/test_constraints.sql

\set ON_ERROR_STOP on
\set QUIET on

BEGIN;

-- Setup test reporting
CREATE TEMP TABLE test_results (
    test_name TEXT,
    status TEXT,
    message TEXT
);

CREATE OR REPLACE FUNCTION run_test(test_name TEXT, test_query TEXT, should_fail BOOLEAN DEFAULT FALSE)
RETURNS VOID AS $$
DECLARE
    error_msg TEXT;
BEGIN
    BEGIN
        EXECUTE test_query;

        IF should_fail THEN
            INSERT INTO test_results VALUES (test_name, 'FAIL', 'Expected error but query succeeded');
        ELSE
            INSERT INTO test_results VALUES (test_name, 'PASS', 'Constraint enforced correctly');
        END IF;
    EXCEPTION WHEN OTHERS THEN
        error_msg := SQLERRM;
        IF should_fail THEN
            INSERT INTO test_results VALUES (test_name, 'PASS', 'Correctly rejected: ' || error_msg);
        ELSE
            INSERT INTO test_results VALUES (test_name, 'FAIL', 'Unexpected error: ' || error_msg);
        END IF;
    END;
END;
$$ LANGUAGE plpgsql;

\echo ''
\echo '===================================='
\echo 'Running Schema Constraint Tests'
\echo '===================================='
\echo ''

-- ================================================================
-- Entity Constraints
-- ================================================================

-- Test: Valid entity creation should succeed
SELECT run_test(
    'Valid entity creation',
    $$INSERT INTO entities (type, name) VALUES ('card', 'Test Card')$$,
    FALSE
);

-- Test: Empty name should fail
SELECT run_test(
    'Empty name rejection',
    $$INSERT INTO entities (type, name) VALUES ('card', '')$$,
    TRUE
);

-- Test: Whitespace-only name should fail
SELECT run_test(
    'Whitespace name rejection',
    $$INSERT INTO entities (type, name) VALUES ('card', '   ')$$,
    TRUE
);

-- Test: Invalid year (too old) should fail
SELECT run_test(
    'Invalid year (too old) rejection',
    $$INSERT INTO entities (type, name, year) VALUES ('card', 'Old Card', 1799)$$,
    TRUE
);

-- Test: Invalid year (future) should fail
SELECT run_test(
    'Invalid year (future) rejection',
    $$INSERT INTO entities (type, name, year) VALUES ('card', 'Future Card', 2101)$$,
    TRUE
);

-- Test: Invalid country code should fail
SELECT run_test(
    'Invalid country code rejection',
    $$INSERT INTO entities (type, name, country) VALUES ('card', 'Test Card', 'USA')$$,
    TRUE
);

-- Test: Valid country code should succeed
SELECT run_test(
    'Valid country code',
    $$INSERT INTO entities (type, name, country) VALUES ('card', 'Test Card', 'US')$$,
    FALSE
);

-- Test: Invalid language code should fail
SELECT run_test(
    'Invalid language code rejection',
    $$INSERT INTO entities (type, name, language) VALUES ('card', 'Test Card', 'eng')$$,
    TRUE
);

-- Test: Valid language code should succeed
SELECT run_test(
    'Valid language code',
    $$INSERT INTO entities (type, name, language) VALUES ('card', 'Test Card', 'en')$$,
    FALSE
);

-- Test: Invalid image_url should fail
SELECT run_test(
    'Invalid image_url rejection',
    $$INSERT INTO entities (type, name, image_url) VALUES ('card', 'Test Card', 'not-a-valid-url')$$,
    TRUE
);

-- Test: Valid storage path should succeed
SELECT run_test(
    'Valid storage path image_url',
    $$INSERT INTO entities (type, name, image_url) VALUES ('card', 'Test Card', '/storage/v1/object/public/images/originals/test.jpg')$$,
    FALSE
);

-- Test: Valid HTTP URL should succeed
SELECT run_test(
    'Valid HTTP URL image_url',
    $$INSERT INTO entities (type, name, image_url) VALUES ('card', 'Test Card', 'https://example.com/image.jpg')$$,
    FALSE
);

-- Test: Thumbnail without image should fail
SELECT run_test(
    'Thumbnail without image rejection',
    $$INSERT INTO entities (type, name, thumbnail_url) VALUES ('card', 'Test Card', '/storage/v1/object/public/images/thumbnails/test.webp')$$,
    TRUE
);

-- Test: Invalid external_ids (not an object) should fail
SELECT run_test(
    'Invalid external_ids (array) rejection',
    $$INSERT INTO entities (type, name, external_ids) VALUES ('card', 'Test Card', '["not", "an", "object"]'::jsonb)$$,
    TRUE
);

-- Test: Valid external_ids object should succeed
SELECT run_test(
    'Valid external_ids object',
    $$INSERT INTO entities (type, name, external_ids) VALUES ('card', 'Test Card', '{"tcgplayer": "base1-4"}'::jsonb)$$,
    FALSE
);

-- ================================================================
-- Relationship Constraints
-- ================================================================

-- Create test entities for relationship tests
INSERT INTO entities (id, type, name) VALUES
    ('00000000-0000-0000-0000-000000000001', 'collection', 'Test Collection'),
    ('00000000-0000-0000-0000-000000000002', 'card', 'Test Card');

-- Test: Valid relationship should succeed
SELECT run_test(
    'Valid relationship creation',
    $$INSERT INTO relationships (from_id, to_id, type) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'contains')$$,
    FALSE
);

-- Test: Self-referential relationship should fail
SELECT run_test(
    'Self-referential relationship rejection',
    $$INSERT INTO relationships (from_id, to_id, type) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'contains')$$,
    TRUE
);

-- Test: Empty relationship type should fail
SELECT run_test(
    'Empty relationship type rejection',
    $$INSERT INTO relationships (from_id, to_id, type) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '')$$,
    TRUE
);

-- Test: Negative order should fail
SELECT run_test(
    'Negative order rejection',
    $$INSERT INTO relationships (from_id, to_id, type, "order") VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'contains', -1)$$,
    TRUE
);

-- Test: Duplicate relationship should fail
SELECT run_test(
    'Duplicate relationship rejection',
    $$INSERT INTO relationships (from_id, to_id, type) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'contains')$$,
    TRUE
);

-- ================================================================
-- Cascade Delete Tests
-- ================================================================

-- Test: Deleting entity should cascade to relationships
INSERT INTO entities (id, type, name) VALUES ('00000000-0000-0000-0000-000000000003', 'card', 'Delete Test');
INSERT INTO relationships (from_id, to_id, type) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', 'contains');

DELETE FROM entities WHERE id = '00000000-0000-0000-0000-000000000003';

SELECT run_test(
    'Cascade delete removes relationships',
    $$SELECT CASE WHEN COUNT(*) = 0 THEN '' ELSE 'Relationships not deleted' END FROM relationships WHERE to_id = '00000000-0000-0000-0000-000000000003'$$,
    FALSE
);

-- ================================================================
-- Print Results
-- ================================================================

\echo ''
\echo 'Test Results:'
\echo '-------------'

SELECT
    test_name,
    CASE
        WHEN status = 'PASS' THEN '✓'
        ELSE '✗'
    END || ' ' || status || ': ' || test_name as result,
    message
FROM test_results
ORDER BY status DESC, test_name;

-- Summary
\echo ''
\echo 'Summary:'
SELECT
    COUNT(*) as total_tests,
    SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
    SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as failed
FROM test_results;

-- Fail the transaction if any tests failed
DO $$
DECLARE
    failed_count INT;
BEGIN
    SELECT COUNT(*) INTO failed_count FROM test_results WHERE status = 'FAIL';
    IF failed_count > 0 THEN
        RAISE EXCEPTION '% test(s) failed', failed_count;
    END IF;
END $$;

ROLLBACK; -- Always rollback to leave database clean

\echo ''
\echo 'All tests passed! ✓'
\echo ''
