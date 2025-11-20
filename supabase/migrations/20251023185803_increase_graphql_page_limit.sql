-- Increase GraphQL pagination limit from default 30 to 1000
-- This matches the max_rows setting for PostgREST API
--
-- The 'first' parameter in GraphQL queries will now accept values up to 1000
-- Default remains 30 if 'first' is not specified

-- Using DO block to handle permission errors gracefully
DO $$
BEGIN
    EXECUTE 'ALTER DATABASE postgres SET graphql.max_page_size = ''1000''';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skipping graphql.max_page_size setting (requires superuser)';
END $$;

-- Note: pg_reload_conf() requires superuser, skipped in local dev
