-- Drop embedding_queue table and related objects
-- This queue-based approach has been replaced by synchronous embedding generation
-- in the MCP tools using Transformers.js

-- Drop the trigger that queued embeddings on entity insert/update
DROP TRIGGER IF EXISTS trigger_queue_embedding ON entities;
DROP FUNCTION IF EXISTS queue_embedding_on_change() CASCADE;

-- Drop the embedding queue table
DROP TABLE IF EXISTS embedding_queue CASCADE;

-- Note: The embedding worker service (services/embedding-worker/) is also deprecated
-- and can be removed from the codebase
