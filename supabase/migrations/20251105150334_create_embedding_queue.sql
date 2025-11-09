-- ================================================================
-- Migration: Create embedding generation queue
-- ================================================================
-- This migration creates a queue-based system for automated embedding
-- generation. When entities are created or their names are updated,
-- they are automatically queued for embedding generation by an
-- external worker service.
-- ================================================================

-- Embedding generation queue table
CREATE TABLE embedding_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    entity_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'MANUAL', 'VERSION_UPGRADE')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    attempts INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    -- Prevent duplicate pending items for the same entity
    -- Allow completed/failed items to coexist for history
    CONSTRAINT unique_pending_entity UNIQUE(entity_id, status)
);

-- Indexes for efficient queue processing
CREATE INDEX idx_embedding_queue_status_priority
ON embedding_queue(status, priority DESC, created_at)
WHERE status = 'pending';

CREATE INDEX idx_embedding_queue_entity_id
ON embedding_queue(entity_id);

CREATE INDEX idx_embedding_queue_processing
ON embedding_queue(processed_at)
WHERE status = 'processing';

-- Comments for documentation
COMMENT ON TABLE embedding_queue IS 'Queue for automated embedding generation. Tracks entities that need embeddings generated or regenerated.';
COMMENT ON COLUMN embedding_queue.operation IS 'Type of operation that triggered the queue entry: INSERT (new entity), UPDATE (name changed), MANUAL (user-triggered), VERSION_UPGRADE (model update)';
COMMENT ON COLUMN embedding_queue.status IS 'Processing status: pending (waiting), processing (being worked on), completed (done), failed (error after max retries)';
COMMENT ON COLUMN embedding_queue.priority IS 'Processing priority. Higher values processed first. Default 0, can be boosted for important items.';
COMMENT ON COLUMN embedding_queue.attempts IS 'Number of processing attempts. Items fail permanently after 3 attempts.';

-- ================================================================
-- Trigger function to automatically queue embeddings
-- ================================================================

CREATE OR REPLACE FUNCTION queue_embedding_generation()
RETURNS TRIGGER AS $$
BEGIN
    -- Only queue if:
    -- 1. New entity with a name (INSERT)
    -- 2. Name changed (UPDATE)
    -- 3. Embedding is missing (UPDATE)
    IF (TG_OP = 'INSERT' AND NEW.name IS NOT NULL) OR
       (TG_OP = 'UPDATE' AND (
           NEW.name IS DISTINCT FROM OLD.name OR
           (NEW.name IS NOT NULL AND NEW.name_embedding IS NULL)
       )) THEN

        -- Insert or update queue entry
        -- Use UPSERT to handle concurrent updates gracefully
        INSERT INTO embedding_queue (
            entity_id,
            entity_name,
            operation,
            priority
        )
        VALUES (
            NEW.id,
            NEW.name,
            TG_OP,
            CASE
                -- Higher priority for certain entity types
                WHEN NEW.type = 'collection' THEN 10
                WHEN NEW.type = 'franchise' THEN 5
                ELSE 0
            END
        )
        ON CONFLICT (entity_id, status)
        WHERE status = 'pending'
        DO UPDATE SET
            entity_name = EXCLUDED.entity_name,
            operation = EXCLUDED.operation,
            priority = GREATEST(embedding_queue.priority, EXCLUDED.priority),
            created_at = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION queue_embedding_generation() IS 'Automatically queues entities for embedding generation when they are created or their names change.';

-- Create trigger on entities table
CREATE TRIGGER trigger_queue_embedding
AFTER INSERT OR UPDATE OF name ON entities
FOR EACH ROW
EXECUTE FUNCTION queue_embedding_generation();

-- ================================================================
-- Worker support functions
-- ================================================================

-- Function to claim items for processing (with row-level locking)
CREATE OR REPLACE FUNCTION claim_embedding_batch(
    batch_size INTEGER DEFAULT 100,
    worker_id TEXT DEFAULT 'default'
)
RETURNS TABLE (
    queue_id UUID,
    entity_id UUID,
    entity_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        SELECT q.id, q.entity_id, q.entity_name
        FROM embedding_queue q
        WHERE q.status = 'pending'
        AND q.attempts < 3  -- Max retry limit
        ORDER BY q.priority DESC, q.created_at
        LIMIT batch_size
        FOR UPDATE SKIP LOCKED  -- Prevents race conditions between workers
    )
    UPDATE embedding_queue q
    SET status = 'processing',
        attempts = attempts + 1,
        processed_at = NOW()
    FROM claimed c
    WHERE q.id = c.id
    RETURNING q.id, q.entity_id, q.entity_name;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION claim_embedding_batch IS 'Claims a batch of pending embeddings for processing. Uses row-level locking to prevent race conditions between multiple workers.';

-- Function to mark items as completed
CREATE OR REPLACE FUNCTION complete_embedding_batch(
    queue_ids UUID[]
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE embedding_queue
    SET status = 'completed',
        processed_at = NOW()
    WHERE id = ANY(queue_ids)
    AND status = 'processing';

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION complete_embedding_batch IS 'Marks a batch of queue items as completed after successful embedding generation.';

-- Function to mark item as failed
CREATE OR REPLACE FUNCTION fail_embedding_item(
    queue_id UUID,
    error_message TEXT
)
RETURNS VOID AS $$
BEGIN
    UPDATE embedding_queue
    SET status = CASE
            WHEN attempts >= 3 THEN 'failed'  -- Permanent failure
            ELSE 'pending'  -- Will retry
        END,
        last_error = error_message,
        processed_at = CASE
            WHEN attempts >= 3 THEN NOW()
            ELSE NULL  -- Reset for retry
        END
    WHERE id = queue_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION fail_embedding_item IS 'Marks a queue item as failed. Items with < 3 attempts are reset to pending for retry.';

-- ================================================================
-- Monitoring and maintenance views
-- ================================================================

-- Real-time queue statistics
CREATE VIEW embedding_queue_stats AS
SELECT
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest,
    MAX(created_at) as newest,
    AVG(EXTRACT(EPOCH FROM (COALESCE(processed_at, NOW()) - created_at))) as avg_wait_seconds,
    MAX(attempts) as max_attempts,
    SUM(CASE WHEN priority > 0 THEN 1 ELSE 0 END) as priority_count
FROM embedding_queue
GROUP BY status;

COMMENT ON VIEW embedding_queue_stats IS 'Real-time statistics for embedding queue monitoring.';

-- Entities missing embeddings
CREATE VIEW entities_missing_embeddings AS
SELECT
    e.id,
    e.name,
    e.type,
    e.created_at,
    e.updated_at,
    eq.status as queue_status,
    eq.attempts as queue_attempts,
    eq.last_error as queue_error
FROM entities e
LEFT JOIN embedding_queue eq ON eq.entity_id = e.id
    AND eq.status IN ('pending', 'processing', 'failed')
WHERE e.name IS NOT NULL
AND e.name_embedding IS NULL
ORDER BY e.created_at;

COMMENT ON VIEW entities_missing_embeddings IS 'Shows all entities that need embeddings, along with their queue status if any.';

-- ================================================================
-- Utility functions for operations
-- ================================================================

-- Manually queue entities missing embeddings
CREATE OR REPLACE FUNCTION queue_missing_embeddings(
    entity_type_filter TEXT DEFAULT NULL,
    batch_limit INTEGER DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    inserted_count INTEGER;
BEGIN
    INSERT INTO embedding_queue (entity_id, entity_name, operation)
    SELECT id, name, 'MANUAL'
    FROM entities
    WHERE name IS NOT NULL
    AND name_embedding IS NULL
    AND (entity_type_filter IS NULL OR type = entity_type_filter)
    ORDER BY created_at
    LIMIT batch_limit
    ON CONFLICT (entity_id, status)
    WHERE status = 'pending'
    DO NOTHING;

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION queue_missing_embeddings IS 'Manually queues entities that are missing embeddings. Useful for backfilling or recovery.';

-- Clean up old completed items
CREATE OR REPLACE FUNCTION cleanup_old_queue_items(
    days_to_keep INTEGER DEFAULT 7
)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM embedding_queue
    WHERE status = 'completed'
    AND processed_at < NOW() - (days_to_keep || ' days')::INTERVAL;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_queue_items IS 'Removes old completed queue items to prevent table bloat. Keeps failed items for debugging.';

-- Retry failed items
CREATE OR REPLACE FUNCTION retry_failed_embeddings(
    max_age_hours INTEGER DEFAULT 24
)
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE embedding_queue
    SET status = 'pending',
        attempts = 0,
        last_error = NULL,
        processed_at = NULL
    WHERE status = 'failed'
    AND created_at > NOW() - (max_age_hours || ' hours')::INTERVAL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION retry_failed_embeddings IS 'Resets failed items back to pending for retry. Useful for recovering from temporary failures.';

-- ================================================================
-- Permissions
-- ================================================================

-- Grant necessary permissions to authenticated users
GRANT SELECT ON embedding_queue TO authenticated;
GRANT SELECT ON embedding_queue_stats TO authenticated, anon;
GRANT SELECT ON entities_missing_embeddings TO authenticated, anon;

-- Grant execute permissions on worker functions
-- Note: In production, create a dedicated worker role with limited permissions
GRANT EXECUTE ON FUNCTION claim_embedding_batch TO authenticated;
GRANT EXECUTE ON FUNCTION complete_embedding_batch TO authenticated;
GRANT EXECUTE ON FUNCTION fail_embedding_item TO authenticated;
GRANT EXECUTE ON FUNCTION queue_missing_embeddings TO authenticated;
GRANT EXECUTE ON FUNCTION cleanup_old_queue_items TO authenticated;
GRANT EXECUTE ON FUNCTION retry_failed_embeddings TO authenticated;