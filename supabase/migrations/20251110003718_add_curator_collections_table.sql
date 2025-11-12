-- Add curator_collections table to track curator-collection relationships
--
-- This table enables:
-- 1. Multi-collection curators (one curator manages multiple collections)
-- 2. Discovery (curator can find all its collections)
-- 3. Introspection (find which curator manages a collection)
--
-- Design:
-- - curator_name: identifies the curator (e.g., "NTSC Video Games")
-- - collection_id: references entities table (can be NULL for free-floating curators)
-- - config: curator-specific parameters (JSONB for flexibility)
--   - NTSC Video Games uses: {"platform_id": 10}
--   - Pokemon TCG might use: {"set_name": "Base Set"}
--   - Marvel Comics might use: {} (empty)

CREATE TABLE public.curator_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    curator_name TEXT NOT NULL,
    collection_id UUID REFERENCES public.entities(id) ON DELETE CASCADE,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for finding all collections managed by a curator
CREATE INDEX idx_curator_collections_curator_name
ON public.curator_collections(curator_name);

-- Index for finding which curator manages a collection
CREATE INDEX idx_curator_collections_collection_id
ON public.curator_collections(collection_id);

-- Unique constraint: one curator cannot manage the same collection twice
CREATE UNIQUE INDEX idx_curator_collections_unique
ON public.curator_collections(curator_name, collection_id);

COMMENT ON TABLE public.curator_collections IS 'Tracks which curators manage which collections. Supports multi-collection curators (e.g., NTSC Video Games serving Game Boy Games, NES Games) and single-collection curators (e.g., Marvel Comics serving Marvel Comics).';

COMMENT ON COLUMN public.curator_collections.curator_name IS 'Name of the curator (matches directory name in .curator/curators/)';

COMMENT ON COLUMN public.curator_collections.collection_id IS 'Collection entity UUID. Can be NULL for free-floating curators.';

COMMENT ON COLUMN public.curator_collections.config IS 'Curator-specific configuration (JSONB). Structure determined by curator during init process. Examples: {"platform_id": 10}, {"set_name": "Base Set"}';
