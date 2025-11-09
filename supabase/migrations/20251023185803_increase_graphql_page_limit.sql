-- Increase GraphQL pagination limit from default 30 to 1000
-- This matches the max_rows setting for PostgREST API
--
-- The 'first' parameter in GraphQL queries will now accept values up to 1000
-- Default remains 30 if 'first' is not specified

ALTER DATABASE postgres SET graphql.max_page_size = '1000';

-- Reload configuration to apply immediately
SELECT pg_reload_conf();
