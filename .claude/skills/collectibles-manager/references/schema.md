# Database Schema Reference

## Tables

### entities

Stores all collectibles, collections, franchises, and related items in a unified table.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `type` | TEXT | Entity type (e.g., `collection`, `trading_card`, `franchise`, `trading_card_game`) |
| `name` | TEXT | Display name (required) |
| `year` | INT | Optional year attribute |
| `country` | CHAR(2) | Optional ISO country code |
| `language` | CHAR(2) | Optional ISO 639-1 language code (e.g., `en`, `ja`, `es`) |
| `image_key` | TEXT | Image storage key or external URL |
| `attributes` | JSONB | Flexible storage for all other attributes |
| `name_embedding` | VECTOR(384) | AI-generated semantic embedding for similarity search (nullable) |
| `created_at` | TIMESTAMPTZ | Auto-generated timestamp |
| `updated_at` | TIMESTAMPTZ | Auto-updated timestamp |

**Common Entity Types:**
- `franchise` - Top-level franchise (e.g., "Pokémon", "Star Wars")
- `trading_card_game` - A TCG system (e.g., "Pokémon Trading Card Game")
- `collection` - A set or collection (e.g., "Base Set", "Scarlet & Violet - 151")
- `trading_card` - Individual cards
- `action_figure` - Action figures or toys
- `sealed_product` - Booster boxes, starter decks, etc.

**Indexes:**
- `idx_entities_type` - Filter by type
- `idx_entities_name` - Exact name lookup
- `idx_entities_name_trgm` - Fuzzy name search
- `idx_entities_language` - Filter by language
- `idx_entities_image_key` - Image key lookups
- `idx_entities_attributes` - JSONB path queries
- `idx_entities_search` - Full-text search
- `idx_entities_name_embedding` - HNSW index for fast vector similarity search

### relationships

Stores connections between entities in a directed graph.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `from_id` | UUID | Parent entity ID (FK to entities) |
| `to_id` | UUID | Child entity ID (FK to entities) |
| `type` | TEXT | Relationship type |
| `order` | INT | Sort order for items in collections (nullable) |
| `attributes` | JSONB | Relationship metadata (additional fields) |
| `created_at` | TIMESTAMPTZ | Auto-generated timestamp |

**Relationship Types (all parent→child):**
- `contains` - Parent contains child (most common)
  - Examples: Collection contains cards, Franchise contains games
- `variant_of` - Variant points to base version
  - Example: "1st Edition Charizard" variant_of "Charizard"
- `part_of` - Component points to whole
  - Example: "Megazord Arm" part_of "Megazord"

**Constraints:**
- Unique constraint on `(from_id, to_id, type)` - prevents duplicate relationships

**Indexes:**
- `idx_relationships_from_type` - Traverse forward (what does X contain?)
- `idx_relationships_to_type` - Traverse backward (what contains X?)
- `idx_relationships_order` - Sort by order
- `idx_relationships_attributes` - Query relationship metadata

## Image Storage

The `image_key` column supports two patterns:

1. **External URLs** - URLs starting with `http://` or `https://`
   - Stored as-is, returned as-is
   - Example: `https://images.pokemontcg.io/base1/4.png`

2. **Supabase Storage paths** - Relative paths
   - Stored as path, converted to full URL via `get_image_url()` function
   - Example: `images/pokemon/charizard.jpg`

### Helper Function: `get_image_url()`

```sql
-- Get full URL from image_key
SELECT get_image_url(image_key) FROM entities;

-- With image transformations
SELECT get_image_url(image_key, 300) FROM entities;  -- width: 300px
SELECT get_image_url(image_key, 300, 400) FROM entities;  -- width: 300px, height: 400px
```

## Common Attributes in JSONB

**Important:** Use dedicated columns for these fields when available:
- Use `entities.language` column instead of `attributes->>'language'`
- Use `relationships.order` column instead of `attributes->>'order'`

### Trading Cards
```json
{
  "card_number": "4/102",
  "rarity": "rare",
  "hp": 120,
  "illustrator": "Artist Name",
  "set_code": "base1",
  "tcgplayer_id": "base1-4"
}
```

**Note:** `language` should be stored in the dedicated `language` column, not in attributes.

### Collections
```json
{
  "release_date": "1999-01-09",
  "total_cards": 102,
  "set_code": "base1"
}
```

**Note:** `language` should be stored in the dedicated `language` column, not in attributes.

### Relationship Attributes
```json
{
  "quantity": 3,
  "condition": "mint"
}
```

**Note:** `order` should be stored in the dedicated `order` column, not in attributes.

## PostgreSQL Extensions

- **uuid-ossp** - UUID generation
- **pg_trgm** - Trigram similarity for fuzzy search
- **pgvector** - Vector similarity search with HNSW indexing

## Semantic Search with Vector Embeddings

The `name_embedding` column stores 384-dimensional vector representations of entity names, enabling semantic similarity search powered by AI.

### How It Works

1. **Embedding Generation**: Entity names are converted to vectors using the `all-MiniLM-L6-v2` sentence-transformer model
2. **Storage**: Vectors are stored in the `name_embedding` column (VECTOR(384) type from pgvector extension)
3. **Indexing**: HNSW (Hierarchical Navigable Small World) index enables fast approximate nearest neighbor search
4. **Querying**: Cosine similarity (`<=>` operator) ranks results by semantic similarity

### Usage Examples

**Generate embeddings for all entities:**
```bash
python scripts/generate_embeddings.py
```

**Search by semantic similarity:**
```bash
# Find entities similar to "fire dragon pokemon"
python scripts/semantic_search.py "fire dragon pokemon"

# Limit to specific type
python scripts/semantic_search.py "base set" --type collection --limit 10
```

**SQL query for semantic search:**
```sql
-- Direct vector search (requires embedding)
SELECT name, type,
       1 - (name_embedding <=> '[0.123, 0.456, ...]'::vector) as similarity
FROM entities
WHERE name_embedding IS NOT NULL
ORDER BY name_embedding <=> '[0.123, 0.456, ...]'::vector
LIMIT 20;

-- Text-based search (recommended)
SELECT * FROM search_by_text('charizard', 'trading_card', 10);
```

**REST API for semantic search:**
```bash
curl -X POST 'http://127.0.0.1:54321/rest/v1/rpc/search_by_text' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "fire dragon pokemon",
    "entity_type_filter": "trading_card",
    "result_limit": 10
  }'
```

**JavaScript/TypeScript client:**
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient('http://127.0.0.1:54321', 'YOUR_ANON_KEY')

const { data, error } = await supabase.rpc('search_by_text', {
  query_text: 'fire dragon pokemon',
  entity_type_filter: 'trading_card',
  result_limit: 10
})
```

**Available PostgreSQL functions:**

- `search_by_text(query_text, entity_type_filter, result_limit)` - Text-based semantic search
  - Accepts plain text queries
  - Returns entities ranked by semantic similarity
  - Exposed via Supabase REST API as RPC endpoint

- `semantic_search(query_embedding, entity_type_filter, result_limit)` - Vector-based search
  - Accepts pre-computed 384-dimensional vectors
  - Lower-level function for advanced use cases

### Benefits

- **Natural language queries**: Search by description ("legendary bird pokemon") instead of exact names
- **Handles typos**: Finds results even with misspellings
- **Cross-language potential**: Can find similar items across languages (depending on model training)
- **Fast performance**: HNSW index enables sub-millisecond searches even with 100k+ entities

### Maintenance

Run `generate_embeddings.py` after:
- Bulk importing new entities
- Adding individual entities (if semantic search is needed for them)
- Changing entity names

The script only generates embeddings for entities where `name_embedding IS NULL`, so it's safe to run multiple times.
