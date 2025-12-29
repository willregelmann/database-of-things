---
name: semantic-search
description: This skill should be used when the user is working with vector embeddings, semantic search, pgvector, CLIP image embeddings, or similarity queries. Examples: "fix semantic search", "generate embeddings", "reverse image search", "search_by_text function", "embedding not working".
analyzed: 2025-12-29
source_files:
  - supabase/migrations/20251105125958_add_vector_embedding.sql
  - supabase/migrations/20251023215655_add_semantic_search_function.sql
  - supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql
  - supabase/migrations/20251130194412_add_category_filter_to_search_functions.sql
  - mcp-server/src/tools/search.ts
  - mcp-server/src/tools/write/embeddings.ts
  - mcp-server/src/tools/write/localize-image.ts
---

# Semantic Search

## What This Domain Does

The database supports semantic search using vector embeddings, enabling searches by meaning rather than exact text matches. Two embedding types are used:

1. **Text embeddings** (384 dimensions): For entity names, using `all-MiniLM-L6-v2` sentence-transformer
2. **Image embeddings** (512 dimensions): For reverse image search, using CLIP `clip-vit-base-patch32`

Both use **pgvector** extension with HNSW indexes for fast approximate nearest neighbor search.

## Key Concepts

- **name_embedding**: 384-dimensional vector on `entities` table for text-based semantic search
- **images.embedding**: 512-dimensional CLIP vector on `images` table for reverse image search
- **pgvector**: PostgreSQL extension for vector operations (cosine distance, HNSW indexing)
- **HNSW Index**: Hierarchical Navigable Small World - efficient approximate nearest neighbor search
- **Transformers.js**: JavaScript library for running transformer models (Xenova/*)

## How It Works

### Text Embeddings

When an entity is created via MCP (`create_entity` or `bulk_import_curator_batch`), the name is automatically converted to a 384-dimensional vector:

```typescript
// In mcp-server/src/tools/write/entities.ts
import { pipeline } from '@xenova/transformers';

const embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
const output = await embedder(entity.name, { pooling: 'mean', normalize: true });
const embedding = Array.from(output.data); // 384 dimensions
```

### Image Embeddings (CLIP)

When an image is localized via MCP (`localize_image` or `bulk_localize_images`), a CLIP embedding is generated:

```typescript
// In mcp-server/src/tools/write/localize-image.ts
import { pipeline } from '@xenova/transformers';

const clipProcessor = await pipeline('image-feature-extraction', 'Xenova/clip-vit-base-patch32');
const imageBuffer = await downloadImage(url);
const output = await clipProcessor(imageBuffer);
const embedding = Array.from(output.data); // 512 dimensions
```

### Search Functions (SQL)

Two PostgreSQL functions provide search capabilities:

**`semantic_search(query_embedding, entity_type_filter, category_filter, result_limit)`**
```sql
SELECT * FROM semantic_search(
  '[0.123, 0.456, ...]'::vector(384),  -- Pre-computed query embedding
  'item',                               -- Optional type filter
  'trading_card_games',                 -- Optional category filter
  20                                    -- Result limit
);
```

**`search_by_text(query_text, entity_type_filter, category_filter, result_limit)`**
```sql
SELECT * FROM search_by_text(
  'fire dragon pokemon',
  'item',
  'trading_card_games',
  20
);
```

**Warning**: `search_by_text` uses trigram matching to find a similar entity, then uses that entity's embedding. It fails for synonyms ("and" vs "&"). Use the MCP tool `search_collectibles` for proper semantic search.

### MCP Search Tool

The `search_collectibles` MCP tool generates embeddings for queries on-the-fly:

```typescript
// In mcp-server/src/tools/search.ts
export async function searchCollectibles(args: {
  query: string;
  entity_type?: string;
  category?: string;
  limit?: number;
}) {
  // Generate embedding for query
  const embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
  const output = await embedder(args.query, { pooling: 'mean', normalize: true });
  const queryEmbedding = Array.from(output.data);

  // Call semantic_search function
  const { data } = await supabase.rpc('semantic_search', {
    query_embedding: `[${queryEmbedding.join(',')}]`,
    entity_type_filter: args.entity_type || null,
    category_filter: args.category || null,
    result_limit: args.limit || 20
  });

  return data;
}
```

## Important Files

- `supabase/migrations/20251105125958_add_vector_embedding.sql`: Creates pgvector extension, name_embedding column, HNSW index
- `supabase/migrations/20251023215655_add_semantic_search_function.sql`: semantic_search function
- `supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql`: Images table with CLIP embeddings
- `supabase/migrations/20251130194412_add_category_filter_to_search_functions.sql`: Adds category filter parameter
- `mcp-server/src/tools/search.ts`: MCP search implementation
- `mcp-server/src/tools/write/localize-image.ts`: CLIP embedding generation

## Working With This Domain

### Checking Embedding Coverage

```sql
-- Count entities with/without embeddings
SELECT
  COUNT(*) FILTER (WHERE name_embedding IS NOT NULL) as with_embedding,
  COUNT(*) FILTER (WHERE name_embedding IS NULL) as without_embedding
FROM entities;

-- Find entities missing embeddings
SELECT id, name, type FROM entities
WHERE name_embedding IS NULL
LIMIT 100;
```

### Backfilling Embeddings

For entities created before automatic embedding generation:

```bash
# Via Python script
python3 scripts/generate-embeddings.py

# Via MCP tool
bulk_generate_embeddings(entity_ids=["uuid1", "uuid2", ...])
```

### Testing Semantic Search

```sql
-- Direct SQL test
SELECT id, name, type, category, round(similarity::numeric, 2) as sim
FROM search_by_text('fire dragon pokemon', 'item', 'trading_card_games', 10);

-- Via MCP
search_collectibles(query="fire dragon pokemon", category="trading_card_games", limit=10)
```

### Index Configuration

```sql
-- Current HNSW index settings
CREATE INDEX idx_entities_name_embedding ON entities
USING hnsw (name_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_images_embedding ON images
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Parameters:**
- `m = 16`: Max connections per node (higher = more accurate, more memory)
- `ef_construction = 64`: Build-time quality (higher = better index, slower build)

### Common Mistakes to Avoid

- **Don't use search_by_text for synonyms**: It won't find "Scarlet and Violet" when searching "Scarlet & Violet"
- **Don't forget to normalize embeddings**: Always use `normalize: true` in Transformers.js
- **Don't mix embedding dimensions**: Text is 384d, images are 512d - they're incompatible
- **Don't search without category filter when possible**: Category filters improve relevance

### Embedding Models

| Purpose | Model | Dimensions | Library |
|---------|-------|------------|---------|
| Text | `Xenova/all-MiniLM-L6-v2` | 384 | @xenova/transformers |
| Image | `Xenova/clip-vit-base-patch32` | 512 | @xenova/transformers |

### Similarity Scoring

Results include a `similarity` score (0-1, where 1 = identical):

```
- 0.95+ : Exact/near-exact match
- 0.85-0.95 : Strong match
- 0.70-0.85 : Good match
- 0.60-0.70 : Weak match
- <0.60 : Poor match
```

For deduplication, use 0.95+ threshold to avoid false positives.

### Reverse Image Search

```sql
-- Find similar images by CLIP embedding
SELECT i.*, 1 - (i.embedding <=> query_embedding) as similarity
FROM images i
WHERE i.embedding IS NOT NULL
ORDER BY i.embedding <=> query_embedding
LIMIT 10;
```

**Note**: `<=>` is the cosine distance operator. Lower distance = higher similarity. Convert to similarity with `1 - distance`.
