-- Increase GraphQL default page size from 30 to 1000
-- This allows queries without explicit 'first' parameter to return more items

-- Set the default page size for pg_graphql
ALTER DATABASE postgres SET graphql.default_page_size = 1000;

-- Also set the maximum page size
ALTER DATABASE postgres SET graphql.max_page_size = 1000;

-- Apply settings to current session
SET graphql.default_page_size = 1000;
SET graphql.max_page_size = 1000;
