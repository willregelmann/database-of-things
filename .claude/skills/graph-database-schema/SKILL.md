---
name: graph-database-schema
description: This skill should be used when the user is working with the database schema, modifying tables, creating migrations, understanding entity relationships, working with JSONB attributes, or asking about the data model. Examples: "adding a column to entities", "creating a new table", "understanding variants vs components", "how relationships work".
analyzed: 2025-12-29
source_files:
  - supabase/migrations/20251020000000_initial_schema.sql
  - supabase/migrations/20251117140439_simplify_schema_with_enums.sql
  - supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql
  - supabase/migrations/20251112171928_create_variants_table.sql
  - supabase/migrations/20251113195527_create_components_table.sql
  - CLAUDE.md
---

# Graph Database Schema

## What This Domain Does

This project uses a **pure graph model** for storing collectibles data. The philosophy is "everything is an entity, connected by relationships." This provides maximum flexibility for heterogeneous collectibles (cards, figures, comics, video games) without schema changes.

The schema consists of seven core tables: `entities`, `relationships`, `variants`, `components`, `images`, and three join tables for additional images.

## Key Concepts

- **entities**: The core table. Everything is an entity - collections, cards, figures, franchises. Uses `entity_type` ENUM ('item' or 'collection') and optional `category_type` ENUM (trading_card_games, figures, comics, video_games, buildables).

- **relationships**: Parent→child connections between entities. All relationships represent "contains" semantics. The `type` column was removed - only `from_id`, `to_id`, and optional `order` remain.

- **variants**: Alternative versions of entities (1st Edition, Shadowless, Holofoil). Stored in dedicated table with `variant_of` FK to entities. NOT stored as separate entities.

- **components**: Physical pieces that can be removed/lost (Zord pieces, LEGO parts, game tokens). Stored in dedicated table with `component_of` FK. Supports `quantity` for bulk items.

- **images**: Centralized image storage with CLIP embeddings. Primary images referenced via `primary_image_id` FK. Additional images via join tables.

## How It Works

### Entity Structure

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type entity_type NOT NULL,           -- 'item' or 'collection'
  category category_type,              -- Optional: trading_card_games, figures, etc.
  name TEXT NOT NULL,
  year INT,
  country CHAR(2),                     -- ISO country code
  language CHAR(2),                    -- ISO 639-1 (en, ja, es)
  primary_image_id UUID REFERENCES images(id),
  source_url TEXT,                     -- Attribution URL
  name_embedding vector(384),          -- For semantic search
  external_ids JSONB DEFAULT '{}',     -- {"pokemontcg_io": "base1-4", "tcgplayer": "123"}
  attributes JSONB DEFAULT '{}',       -- All other metadata
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

### Relationship Direction

Relationships flow **parent → child** (contains direction):
- Collection → Card
- Franchise → Game → Expansion → Card
- Use `from_id` for "what does this contain?"
- Use `to_id` for "what contains this?"

```sql
-- Get items in a collection
SELECT e.* FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid';

-- Get parents of an item
SELECT e.* FROM entities e
JOIN relationships r ON r.from_id = e.id
WHERE r.to_id = 'item-uuid';
```

### JSONB Columns

Two separate JSONB columns exist on entities:

1. **external_ids**: External system identifiers for deduplication
   ```json
   {"pokemontcg_io": "base1-4", "tcgplayer": "base1-4", "metron_id": "60339"}
   ```

2. **attributes**: All other flexible metadata
   ```json
   {"hp": 120, "card_number": "4/102", "rarity": "rare", "description": "..."}
   ```

**Important**: Use dedicated columns when available (`name`, `year`, `country`, `language`, `source_url`), not JSONB attributes.

### Images Architecture

Images are stored in a centralized `images` table:

```sql
CREATE TABLE images (
  id UUID PRIMARY KEY,
  image_url TEXT NOT NULL,      -- /storage/v1/object/public/images/originals/uuid.jpg
  thumbnail_url TEXT,           -- /storage/v1/object/public/images/thumbnails/uuid.webp
  embedding vector(512),        -- CLIP embedding for reverse image search
  source_url TEXT,              -- Attribution
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

- **Primary image**: `entities.primary_image_id`, `variants.primary_image_id`, `components.primary_image_id`
- **Additional images**: Join tables (`entity_additional_images`, `variant_additional_images`, `component_additional_images`)

## Important Files

- `supabase/migrations/20251020000000_initial_schema.sql`: Original entities + relationships
- `supabase/migrations/20251117140439_simplify_schema_with_enums.sql`: Adds entity_type/category_type ENUMs, removes relationships.type
- `supabase/migrations/20251114221309_add_images_table_and_reverse_image_search.sql`: Creates images table and join tables
- `supabase/migrations/20251112171928_create_variants_table.sql`: Variants table
- `supabase/migrations/20251113195527_create_components_table.sql`: Components table
- `supabase/config.toml`: Supabase configuration

## Working With This Domain

### When Adding New Columns

1. Always create a migration: `./bin/supabase migration new add_column_name`
2. Use `./scripts/safe-migrate push` to apply (creates automatic backup)
3. Update CLAUDE.md to document the new column
4. Consider: Should this be a dedicated column or go in `attributes` JSONB?

### When Querying Relationships

```sql
-- Traverse hierarchy recursively
WITH RECURSIVE hierarchy AS (
  SELECT id, name, type, 0 as level
  FROM entities WHERE name = 'Pokemon TCG'
  UNION ALL
  SELECT e.id, e.name, e.type, h.level + 1
  FROM entities e
  JOIN relationships r ON r.to_id = e.id
  JOIN hierarchy h ON r.from_id = h.id
)
SELECT * FROM hierarchy ORDER BY level, name;
```

### Common Mistakes to Avoid

- **Don't create variants as entities**: Use the `variants` table, not entities with relationships
- **Don't create components as entities**: Use the `components` table
- **Don't store external IDs in attributes**: Use the dedicated `external_ids` JSONB column
- **Don't use relationships.type**: It was removed - all relationships are "contains"
- **Don't forget cascade deletes**: Deleting an entity cascades to relationships, variants, components

### Entity Type vs Category

- **type** (required): 'item' or 'collection' - structural classification
- **category** (optional): Domain classification (trading_card_games, figures, comics, video_games, buildables)

A trading card is `type='item', category='trading_card_games'`
A Pokemon TCG expansion is `type='collection', category='trading_card_games'`

### Indexes Available

```sql
-- Entity lookups
idx_entities_type              -- Filter by type
idx_entities_category          -- Filter by category (partial)
idx_entities_name              -- Exact name
idx_entities_name_trgm         -- Fuzzy search (GIN trigram)
idx_entities_name_embedding    -- Semantic search (HNSW)
idx_entities_external_ids      -- External ID queries (GIN)
idx_entities_attributes        -- Attribute queries (GIN)

-- Relationship traversal
idx_relationships_from_id      -- Forward traversal
idx_relationships_to_id        -- Reverse traversal
```
