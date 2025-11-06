-- Curator registry
CREATE TABLE curators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    collection_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}',
    plan_version INT DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Operation log (for rollback/resume)
CREATE TABLE curator_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID REFERENCES curators(id) ON DELETE CASCADE,
    run_id UUID NOT NULL,
    operation_type TEXT NOT NULL,
    entity_id UUID,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'rolled_back')),
    data JSONB,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Run history
CREATE TABLE curator_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_id UUID REFERENCES curators(id) ON DELETE CASCADE,
    trigger TEXT NOT NULL CHECK (trigger IN ('manual', 'scheduled', 'mini-discovery')),
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'rolled_back')),
    operations_count INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error TEXT,
    summary JSONB
);

-- Indexes for performance
CREATE INDEX idx_curator_operations_run ON curator_operations(run_id);
CREATE INDEX idx_curator_operations_status ON curator_operations(status) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_curator_runs_curator ON curator_runs(curator_id, started_at DESC);
CREATE INDEX idx_curators_status ON curators(status) WHERE status != 'paused';
CREATE INDEX idx_curators_next_run ON curators(next_run_at) WHERE status = 'active' AND next_run_at IS NOT NULL;

-- Row Level Security (public read for curator metadata, service role write)
ALTER TABLE curators ENABLE ROW LEVEL SECURITY;
ALTER TABLE curator_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE curator_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access to curators"
    ON curators FOR SELECT USING (true);

CREATE POLICY "Public read access to curator_runs"
    ON curator_runs FOR SELECT USING (true);

-- No public access to operations (internal audit log)

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER curators_updated_at
    BEFORE UPDATE ON curators
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Comments for documentation
COMMENT ON TABLE curators IS 'Curator agents managing collections';
COMMENT ON TABLE curator_operations IS 'Audit log of all curator operations for rollback/resume';
COMMENT ON TABLE curator_runs IS 'History of curator run executions';
COMMENT ON COLUMN curators.config IS 'Curator configuration: {dedup_threshold: 0.93, schedule: "0 2 * * *", etc}';
COMMENT ON COLUMN curator_operations.data IS 'Operation details: entity data, image URLs, relationship info, etc';
COMMENT ON COLUMN curator_runs.summary IS 'Run summary: {entities_added: 42, duplicates_found: 3, errors: []}';
