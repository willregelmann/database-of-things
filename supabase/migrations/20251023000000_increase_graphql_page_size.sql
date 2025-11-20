-- Increase GraphQL default page size from 30 to 1000
-- This allows queries without explicit 'first' parameter to return more items

-- Set the default page size for pg_graphql (requires elevated permissions)
-- Using DO block to handle permission errors gracefully
DO $$
BEGIN
    EXECUTE 'ALTER DATABASE postgres SET graphql.default_page_size = 1000';
    EXECUTE 'ALTER DATABASE postgres SET graphql.max_page_size = 1000';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Skipping graphql page size settings (requires superuser)';
END $$;
