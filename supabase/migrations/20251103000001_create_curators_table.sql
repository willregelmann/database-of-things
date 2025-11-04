-- Phase 3: Curators Management Tables
--
-- Creates tables for managing autonomous curators:
-- - curators: Core curator metadata (minimal, most data in S3)
-- - curator_runs: Run history and execution results

-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- Curators Table
-- =====================================================
-- Stores minimal curator metadata. Most configuration (schema, workflow,
-- discovery reports, generated code) is stored in S3/Supabase Storage.

CREATE TABLE IF NOT EXISTS curators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,  -- Human-readable name (e.g., "elden-ring-curator")
    collection_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    instructions TEXT,  -- Original user instructions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_run_at TIMESTAMP WITH TIME ZONE,
    total_runs INTEGER DEFAULT 0
);

-- Index for fast lookup by name
CREATE INDEX IF NOT EXISTS idx_curators_name ON curators(name);

-- Index for finding curators by collection
CREATE INDEX IF NOT EXISTS idx_curators_collection_id ON curators(collection_id);

-- Index for sorting by last run
CREATE INDEX IF NOT EXISTS idx_curators_last_run ON curators(last_run_at DESC);

-- =====================================================
-- Curator Runs Table
-- =====================================================
-- Tracks execution history for each curator.
-- Detailed results (logs, import stats) stored in S3.

CREATE TABLE IF NOT EXISTS curator_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID NOT NULL REFERENCES curators(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    products_imported INTEGER DEFAULT 0,
    custom_instructions TEXT,  -- Run-specific instructions (optional)
    results_url TEXT,  -- S3 URL to detailed results
    error_message TEXT  -- Error details if failed
);

-- Index for finding runs by curator
CREATE INDEX IF NOT EXISTS idx_curator_runs_curator_id ON curator_runs(curator_id);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_curator_runs_status ON curator_runs(status);

-- Index for sorting by start time
CREATE INDEX IF NOT EXISTS idx_curator_runs_started_at ON curator_runs(started_at DESC);

-- =====================================================
-- Triggers
-- =====================================================

-- Auto-update updated_at timestamp on curators
CREATE OR REPLACE FUNCTION update_curators_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER curators_updated_at
    BEFORE UPDATE ON curators
    FOR EACH ROW
    EXECUTE FUNCTION update_curators_updated_at();

-- Update curator stats when a run completes
CREATE OR REPLACE FUNCTION update_curator_stats_on_run()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if status changed to completed
    IF NEW.status = 'completed' AND (OLD.status IS NULL OR OLD.status != 'completed') THEN
        UPDATE curators
        SET
            last_run_at = NEW.completed_at,
            total_runs = total_runs + 1
        WHERE id = NEW.curator_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER curator_runs_update_stats
    AFTER INSERT OR UPDATE ON curator_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_curator_stats_on_run();

-- =====================================================
-- Comments
-- =====================================================

COMMENT ON TABLE curators IS 'Autonomous curator agents that manage data imports. Most configuration stored in S3.';
COMMENT ON COLUMN curators.name IS 'Unique human-readable identifier (e.g., "elden-ring-curator")';
COMMENT ON COLUMN curators.instructions IS 'Original user instructions that initialized the curator';
COMMENT ON TABLE curator_runs IS 'Execution history for curators. Detailed results in S3.';
COMMENT ON COLUMN curator_runs.results_url IS 'S3 URL to full results JSON (logs, stats, artifacts)';
