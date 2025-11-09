-- ================================================================
-- Migration: Add Public Read-Only RLS
-- ================================================================
-- Simple security model for curator-only writes, public reads
--
-- Model:
-- - All data is public (no user_id needed)
-- - Anonymous users can read
-- - Only service role can write (via admin API key)
-- - Prevents accidental deletes from client

-- ================================================================
-- Enable Row Level Security
-- ================================================================

ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE relationships ENABLE ROW LEVEL SECURITY;

-- ================================================================
-- Public Read Policies
-- ================================================================

-- Anyone can read entities (no auth required)
CREATE POLICY "Public read access to entities"
    ON entities
    FOR SELECT
    USING (true);

-- Anyone can read relationships
CREATE POLICY "Public read access to relationships"
    ON relationships
    FOR SELECT
    USING (true);

-- ================================================================
-- Admin Write Policies
-- ================================================================
-- By default, only service_role can write when RLS is enabled
-- and no INSERT/UPDATE/DELETE policies exist for anon/authenticated
--
-- This means:
-- - Client apps with anon key: read-only ✓
-- - Admin scripts with service_role key: full access ✓
-- - Accidental client deletes: blocked ✓

-- Optionally, allow authenticated admin user to write:
-- (Uncomment if you want to allow specific authenticated users to write)

-- CREATE POLICY "Authenticated admins can insert entities"
--     ON entities
--     FOR INSERT
--     TO authenticated
--     WITH CHECK (
--         -- Only specific user IDs can write
--         auth.uid() IN (
--             'your-admin-user-id-here'
--         )
--     );

-- CREATE POLICY "Authenticated admins can update entities"
--     ON entities
--     FOR UPDATE
--     TO authenticated
--     USING (
--         auth.uid() IN (
--             'your-admin-user-id-here'
--         )
--     );

-- CREATE POLICY "Authenticated admins can delete entities"
--     ON entities
--     FOR DELETE
--     TO authenticated
--     USING (
--         auth.uid() IN (
--             'your-admin-user-id-here'
--         )
--     );

-- ================================================================
-- Storage Bucket Policies
-- ================================================================

-- Public read access to images
CREATE POLICY "Public read access to images"
    ON storage.objects
    FOR SELECT
    USING (bucket_id = 'images');

-- Only service role can upload/delete images
-- (No policy needed - service_role bypasses RLS)

-- ================================================================
-- Verification
-- ================================================================

-- Test public read access (as anonymous user)
-- This should work:
-- curl "https://your-project.supabase.co/rest/v1/entities?select=id,name"
--   -H "apikey: your-anon-key"

-- Test write protection (as anonymous user)
-- This should fail:
-- curl -X POST "https://your-project.supabase.co/rest/v1/entities"
--   -H "apikey: your-anon-key"
--   -H "Content-Type: application/json"
--   -d '{"name": "Test", "type": "card"}'

COMMENT ON POLICY "Public read access to entities" ON entities IS
    'Allow anyone to read entities without authentication. Writes require service_role key.';

COMMENT ON POLICY "Public read access to relationships" ON relationships IS
    'Allow anyone to read relationships without authentication.';
