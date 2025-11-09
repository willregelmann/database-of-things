-- ================================================================
-- Migration: Add vector embeddings for semantic search
-- ================================================================
-- Enables semantic search using pgvector extension.
-- Adds name_embedding column to store 384-dimensional embeddings
-- (compatible with sentence-transformers/all-MiniLM-L6-v2 model)
--
-- IMPORTANT: Embeddings must be generated externally (e.g., Python script)
-- and inserted via application code. This migration only creates the schema.
-- ================================================================

-- Enable pgvector extension for vector operations
CREATE EXTENSION IF NOT EXISTS vector;

-- Add name_embedding column to entities table
-- 384 dimensions matches sentence-transformers/all-MiniLM-L6-v2 model
ALTER TABLE entities
ADD COLUMN IF NOT EXISTS name_embedding vector(384);

-- Create HNSW index for fast approximate nearest neighbor search
-- Using cosine distance (1 - cosine similarity) for similarity comparison
-- HNSW (Hierarchical Navigable Small World) is optimal for high-dimensional vectors
CREATE INDEX IF NOT EXISTS idx_entities_name_embedding
ON entities
USING hnsw (name_embedding vector_cosine_ops);

-- Add documentation
COMMENT ON COLUMN entities.name_embedding IS 'Vector embedding of entity name (384 dimensions) for semantic similarity search. Generated using sentence-transformers/all-MiniLM-L6-v2 or similar model. Use semantic_search() or search_by_text() functions to query.';
