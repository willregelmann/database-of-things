# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal, pure graph database for managing collectibles using PostgreSQL via Supabase. The architecture is intentionally simple: just entities and relationships with JSONB attributes for flexibility.

**Core Philosophy**: Everything is an entity (collections, items, variants, etc.), connected by typed relationships. No fixed schema beyond the essentials.

## Project Philosophy & Vision

### Why a Pure Graph Model?

Traditional relational schemas force collectibles into rigid hierarchies. Real collectibles don't work that way:

- **Many-to-many relationships**: Pokemon Red Version belongs to both "Game Boy Games" and "Pokemon Generation I" collections
- **Arbitrary nesting**: Franchises contain games, games contain sets, sets contain cards - but also cross-collection relationships
- **Heterogeneous items**: Cards, toys, games, and comics all coexist without schema changes

The pure graph model provides **maximum flexibility** while remaining conceptually simple. Three tables, infinite possibilities.

### Data Integrity Philosophy

**Relationships**:
- Support arbitrarily deep nesting (franchise → game → collection → item)
- Allow many-to-many relationships (one item, multiple parent collections)
- Carefully avoid circular references (managed through data integrity, not schema constraints)

**Metadata**:
- **Minimal by design**: Focus on coverage and relationships over exhaustive details
- **Source attribution**: Every entity tracks `source_url` for data provenance
- **External IDs**: Preserve original system identifiers for reconciliation
- **Curator-specific consistency**: Within a collection, metadata fields are standardized (e.g., all video games have "publisher" and "developers")

### Long-Term Vision

**Mission**: Build the most comprehensive collectibles database on the Internet.

**Goals**:
1. **Coverage**: Every collectible ever made, across all categories
2. **Relationship richness**: Connect items through franchises, variants, components, and cross-references
3. **Public resource**: Free read-only access for anyone building collectibles applications
4. **Sustainable**: Automated curator system for imports, updates, and reconciliation

**Use cases we're enabling**:
- Price tracking apps that need comprehensive item catalogs
- Collection management tools that leverage our relationship graph
- Market research analyzing collectibles trends across categories
- Educational resources exploring collectibles history

**Not optimizing for**:
- Exhaustive metadata (descriptions, detailed specs) - that's what source links are for
- Real-time market data - we're a catalog, not a marketplace
- User-generated content - curators maintain data quality

## Development Commands

### Supabase Local Development

```bash
# Start full Supabase stack (PostgreSQL, Auth, Storage, Realtime, GraphQL, REST APIs, Studio UI)
./bin/supabase start

# Stop all services
./bin/supabase stop

# Check status
./bin/supabase status

# View logs
./bin/supabase logs
```

**Note:** For database migrations and resets, see "Database Operations" section below. Always use `./scripts/safe-migrate` to ensure automatic backups.

### Database Operations

```bash
# Access PostgreSQL CLI
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres

# Create a new migration file
./bin/supabase migration new migration_name

# Apply migrations (SAFE - preserves data)
./scripts/safe-migrate push

# Reset database (DESTRUCTIVE - requires confirmation)
./scripts/safe-migrate reset

# Generate migration from schema changes
./bin/supabase db diff -f migration_name

# Manual backup (creates timestamped backup in backups/)
./scripts/db-backup

# Restore from backup
./scripts/db-restore backups/backup_YYYYMMDD_HHMMSS.sql

# Backup Supabase storage bucket
./scripts/storage-backup

# Restore Supabase storage bucket
./scripts/storage-restore backups/storage_backup_YYYYMMDD_HHMMSS.tar.gz

# Repair migration issues (if needed)
./scripts/repair-migrations

# Generate thumbnails for all images
./scripts/generate-all-thumbnails
```

### ⚠️ CRITICAL: Database Safety

**ALWAYS use `./scripts/safe-migrate` instead of direct `./bin/supabase db` commands!**

- ✅ Auto-creates backups before migrations (stored in `backups/` with timestamps)
- ✅ Requires confirmation for destructive operations
- ⚠️ `./bin/supabase db reset` **DESTROYS ALL DATA** without warning - use `./scripts/safe-migrate reset` instead

**Recovery:** `./scripts/db-restore backups/backup_YYYYMMDD_HHMMSS.sql`

### Data Seeding & Testing

```bash
# Seed local database with sample data (24 entities, 6 variants)
python3 scripts/seed-sample-data.py

# NOTE: Embeddings are now generated automatically when entities are created
# No manual embedding generation needed for new data!
# (For backfill of existing data: python3 scripts/generate-embeddings.py)

# Test semantic search via SQL
docker exec supabase_db_database-of-things psql -U postgres -d postgres \
  -c "SELECT name, category, round(similarity::numeric, 2) FROM search_by_text('pokemon', 'item', 'trading_card_games', 5);"

# Verify schema synchronization between local and production
./scripts/verify-schema-sync.sh
```

**Seeded Data Includes:**
- 4 top-level collections (Pokemon TCG, Power Rangers Toys, Marvel Comics, Video Games)
- 4 sub-collections with nested relationships
- 16 collectible items across different types (cards, figures, comics, video games)
- 6 variants demonstrating the variants table
- All entities include embeddings for semantic search

### Migration Tracking Best Practices

**ALWAYS use Supabase CLI for migrations:**
```bash
# Create new migration
./bin/supabase migration new feature_name

# Apply locally
./bin/supabase db push

# Apply to production
./bin/supabase db push --linked

# Check migration status
./bin/supabase migration list --linked
```

**NEVER:**
- ❌ Apply migrations via Supabase Dashboard SQL Editor (bypasses tracking)
- ❌ Use direct psql for schema changes
- ❌ Skip creating migration files

**If migration tracking gets out of sync:**
```bash
# Repair local tracking (mark as applied without running)
docker exec supabase_db_database-of-things psql -U postgres -d postgres << 'SQL'
INSERT INTO supabase_migrations.schema_migrations (version)
VALUES ('20251112171928') ON CONFLICT DO NOTHING;
SQL

# For production, use scripts/fix-production-migrations.sql in Dashboard
```

See `MIGRATION_STATUS.md` for current migration tracking status.

## Supabase Stack Access

When running (`./bin/supabase start`), you get:

- **Studio UI**: http://127.0.0.1:54323
  - Visual database editor, table browser, SQL editor

- **GraphQL API**: http://127.0.0.1:54321/graphql/v1
  - Auto-generated from database schema
  - Use apikey: `sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH` (from `supabase status`)

- **REST API**: http://127.0.0.1:54321/rest/v1
  - PostgREST auto-generated endpoints

- **Storage API**: http://127.0.0.1:54321/storage/v1
  - S3-compatible object storage for images
  - S3 URL: http://127.0.0.1:54321/storage/v1/s3

- **Database**: postgresql://postgres:postgres@127.0.0.1:54322/postgres

- **Mailpit** (Email Testing): http://127.0.0.1:54324

**Note**: API keys and secrets are shown when you run `./bin/supabase status`. These are local development keys only.

## Database Architecture

### Pure Graph Model

The schema consists of seven tables:

**`entities`** - Collections and items in the system:
- `id` (UUID): Primary key
- `type` (entity_type ENUM): Entity type - either "item" or "collection"
- `category` (category_type ENUM): Optional category - trading_card_games, figures, comics, video_games, or buildables (nullable, can apply to both items and collections)
- `name` (TEXT): Display name
- `year` (INT): Optional universal year attribute
- `country` (CHAR(2)): Optional ISO country code
- `language` (CHAR(2)): Optional ISO 639-1 language code (e.g., "en", "ja", "es")
- `primary_image_id` (UUID): Foreign key to images table for main image (nullable)
- `source_url` (TEXT): Source page URL where entity data was obtained (for attribution)
- `name_embedding` (vector(384)): Vector embedding for semantic search (nullable, **generated automatically** on entity creation via Transformers.js)
- `external_ids` (JSONB): External system IDs (e.g., `{"tcgplayer": "base1-4", "pokemontcg_io": "base1-4"}`)
- `attributes` (JSONB): All other data (description, custom fields)
- Timestamps: `created_at`, `updated_at`

**`images`** - Unified image storage with embeddings:
- `id` (UUID): Primary key
- `image_url` (TEXT): Image URL path - local storage uses `/storage/v1/object/public/images/originals/uuid.ext`, external URLs stored as-is
- `thumbnail_url` (TEXT): Optional pre-generated thumbnail path (typically 300x300 WebP) - `/storage/v1/object/public/images/thumbnails/uuid.webp`
- `embedding` (vector(512)): CLIP image embedding for reverse image search (nullable, **generated automatically** via Transformers.js)
- `source_url` (TEXT): Attribution/provenance URL
- Timestamps: `created_at`, `updated_at`

**`entity_additional_images`**, **`variant_additional_images`**, **`component_additional_images`** - Join tables for additional images:
- Parent ID (entity_id/variant_id/component_id): Foreign key (CASCADE delete)
- `image_id` (UUID): Foreign key to images table (CASCADE delete)
- `order` (INT): Optional sort order for display (nullable)
- Primary key: `(parent_id, image_id)`

**`variants`** - Alternative versions of entities (e.g., 1st Edition, Shadowless):
- `id` (UUID): Primary key
- `variant_of` (UUID): Foreign key to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Variant name (e.g., "1st Edition", "Shadowless")
- `primary_image_id` (UUID): Foreign key to images table for main image (nullable)
- `attributes` (JSONB): Variant-specific metadata (edition, print run, condition, etc.)
- Timestamps: `created_at`, `updated_at`

**`components`** - Physical pieces that can be removed/lost from items:
- `id` (UUID): Primary key
- `component_of` (UUID): Foreign key to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Component name (e.g., "Red Ranger Zord", "Wooden Tokens")
- `quantity` (INTEGER): How many of this component (default 1)
- `order` (INTEGER): Optional sort order for display
- `primary_image_id` (UUID): Foreign key to images table for main image (nullable)
- `attributes` (JSONB): Component metadata (condition notes, materials, physical specs)
- Timestamps: `created_at`, `updated_at`

**`relationships`** - Connections between entities:
- `id` (UUID): Primary key
- `from_id` (UUID): Source entity
- `to_id` (UUID): Target entity
- `order` (INT): Sort order for items in collections (nullable)
- `created_at` timestamp
- UNIQUE constraint on `(from_id, to_id)`
- **Note**: The `type` column was removed in migration `20251117140439_simplify_schema_with_enums.sql` - all relationships now represent a single "contains" semantic. The `attributes` JSONB column was removed in migration `20251024195010_drop_relationships_attributes.sql` as it was unused.

### Design Patterns

**Images Architecture**:
- **Centralized storage**: All images (entity, variant, component) stored in single `images` table
- **Primary images**: Referenced via `primary_image_id` foreign key (entities, variants, components)
- **Additional images**: Join tables (`entity_additional_images`, etc.) for multiple images per item
- **Image embeddings**: 512d CLIP embeddings generated automatically for reverse image search
- **URL pattern**: Local images in `/storage/v1/object/public/images/{originals|thumbnails}/uuid.{ext}`
- Access images via GraphQL computed fields: `entity_primary_image()`, `entity_additional_images()`

**JSONB Attributes Philosophy**:
- Only universally applicable fields are columns (`name`, `type`, `year`, `country`, `language`, `primary_image_id`)
- External system IDs are stored in dedicated `external_ids` JSONB column (not in `attributes`)
- For relationships, commonly-used fields like `order` are dedicated columns
- Everything else goes in `attributes` JSONB (description, custom metadata)
- Allows heterogeneous entity types without schema changes
- **Important**: Always use dedicated columns when available instead of JSONB attributes
- **Relationships**: The `relationships` table has NO attributes column - all relationship metadata must use dedicated columns (currently only `order` exists)

**Variants Architecture**:
- Variants are stored in dedicated table, not as entities
- `variant_of` foreign key is mandatory (NOT NULL)
- CASCADE delete ensures variants removed when base entity deleted
- Access via `entity_variants()` GraphQL computed field
- **Note**: JSONB filtering on variants.attributes does NOT work in GraphQL (PostgREST limitation) - use SQL queries for attribute filtering
- Legacy: Some older variant data may exist as entities with `variant_of` relationships

**Components Architecture**:
- Components stored in dedicated table, not as entities
- `component_of` foreign key is mandatory (NOT NULL)
- CASCADE delete ensures components removed when parent entity deleted
- Access via `entity_components()` GraphQL computed field
- Quantity tracking for bulk items (e.g., 50 tokens vs. 1 unique piece)
- Optional ordering for assembly instructions or logical grouping
- Legacy: Some older component data may exist as entities with `part_of` relationships

**Relationships Semantics**:
- All relationships represent a "contains" relationship (parent→child direction)
- Example: Collection → Card, Franchise → Game, Collection → Sub-Collection
- Makes querying intuitive: "show me what this collection contains"
- For variants and components, use the dedicated `variants` and `components` tables instead of relationships

**Graph Traversal**:
- Use `from_id` for forward traversal (what does this entity contain?)
- Use `to_id` for reverse traversal (what contains this entity?)
- Indexes `idx_relationships_from_id` and `idx_relationships_to_id` optimized for both directions

### PostgreSQL Extensions

- **uuid-ossp**: UUID generation (`uuid_generate_v4()`)
- **pg_trgm**: Trigram similarity for fuzzy name matching
- **vector**: pgvector extension for vector embeddings and similarity search (cosine distance, HNSW indexing)

### Indexes

**Entity lookups**:
- `idx_entities_type`: Filter by entity type
- `idx_entities_category`: Filter by category (partial index, only non-null values)
- `idx_entities_name`: Exact name lookup
- `idx_entities_name_trgm`: Fuzzy name search (GIN trigram)
- `idx_entities_name_embedding`: Semantic search (HNSW with cosine distance)
- `idx_entities_language`: Filter by language (partial index, only non-null values)
- `idx_entities_attributes`: JSONB path queries on attributes (GIN)
- `idx_entities_external_ids`: JSONB queries on external_ids (GIN)
- `idx_entities_search`: Full-text search on name

**Relationship traversal**:
- `idx_relationships_from_id`: Find all children of an entity (what it contains)
- `idx_relationships_to_id`: Find all parents of an entity (what contains it)
- `idx_relationships_order`: Sort by order (partial index, only non-null values)

**Variant lookups**:
- `idx_variants_variant_of`: Find all variants of a base entity
- `idx_variants_attributes`: JSONB queries on variant metadata (GIN)

**Component lookups**:
- `idx_components_component_of`: Find all components of a parent entity
- `idx_components_order`: Sort by order (partial index, only non-null values)
- `idx_components_attributes`: JSONB queries on component metadata (GIN)

**Image lookups**:
- `idx_images_embedding`: Reverse image search (HNSW with cosine distance, 512d CLIP embeddings)
- `idx_entity_additional_images_entity`: Find additional images for an entity
- `idx_entity_additional_images_order`: Sort additional images by order (partial index)
- Similar indexes for `variant_additional_images` and `component_additional_images`

## Semantic Search

The database supports semantic search using vector embeddings, allowing you to find similar entities based on meaning rather than exact text matches.

### How It Works

1. **Embeddings**: Entity names are converted to 384-dimensional vectors using a sentence-transformer model (e.g., `all-MiniLM-L6-v2`)
2. **Storage**: Vectors stored in `name_embedding` column
3. **Indexing**: HNSW (Hierarchical Navigable Small World) index enables fast approximate nearest neighbor search
4. **Similarity**: Uses cosine distance (1 - cosine similarity) to find semantically similar entities

### Search Functions

**`semantic_search(query_embedding, entity_type_filter, category_filter, result_limit)`** - Vector-based search:
```sql
-- Search using a pre-computed embedding vector
SELECT * FROM semantic_search(
  '[0.123, 0.456, ...]'::vector(384),  -- Your query embedding
  'item',                               -- Optional: filter by type ('item' or 'collection')
  'trading_card_games',                 -- Optional: filter by category
  20                                    -- Limit results
);

-- Search all categories, just filter by type
SELECT * FROM semantic_search(
  '[0.123, 0.456, ...]'::vector(384),
  'item',
  NULL,  -- No category filter
  20
);
```

**`search_by_text(query_text, entity_type_filter, category_filter, result_limit)`** - Text-based search:
```sql
-- Search using plain text (finds closest entity name, uses its embedding)
SELECT * FROM search_by_text(
  'fire dragon pokemon',  -- Plain text query
  'item',                 -- Optional: filter by type ('item' or 'collection')
  'trading_card_games',   -- Optional: filter by category
  20                      -- Limit results
);

-- Search figures only
SELECT * FROM search_by_text('megazord', NULL, 'figures', 10);
```

**Available categories**: `trading_card_games`, `figures`, `comics`, `video_games`, `buildables`

**⚠️ WARNING**: `search_by_text()` has limitations because it uses trigram text matching to find a similar entity first, then uses that entity's embedding. This means it fails for synonyms and variations (e.g., "scarlet and violet" won't find "Scarlet & Violet").

**Use MCP tools for proper semantic search.** The `search_collectibles` MCP tool generates embeddings for queries, handling synonyms and semantic variations.

### MCP Semantic Search (Recommended)

Use the `search_collectibles` MCP tool for true semantic search:

```
mcp__database-of-things-local__search_collectibles
  query: "fire dragon pokemon"
  category: "trading_card_games"  # Optional: filter by category
  entity_type: "item"              # Optional: filter by type
  limit: 10
```

**Why use this?**
- ✅ Handles synonyms and variations ("and" vs "&", "pokemon" vs "pokémon")
- ✅ Understands semantic meaning ("fire dragon" finds Charizard)
- ✅ Supports category filtering (trading_card_games, figures, comics, etc.)
- ✅ Returns images with results

### GraphQL Examples

```graphql
# Semantic search with vector embedding and category filter
query {
  semantic_search(
    args: {
      query_embedding: "[0.123, 0.456, ...]"
      entity_type_filter: "item"
      category_filter: "trading_card_games"
      result_limit: 20
    }
  ) {
    id
    name
    type
    category
    similarity
    image_url
    thumbnail_url
  }
}

# Text-based semantic search with category filter
query {
  search_by_text(
    args: {
      query_text: "fire dragon pokemon"
      entity_type_filter: "item"
      category_filter: "trading_card_games"
      result_limit: 20
    }
  ) {
    id
    name
    type
    category
    similarity
  }
}
```

### Generating Embeddings

**Embeddings are now generated automatically:**

- **Text embeddings** (384d): Generated automatically via Transformers.js when calling `create_entity` MCP tool
- **Image embeddings** (512d): Generated automatically via Transformers.js when calling `localize_image` MCP tool

**No manual embedding generation required** for new entities or images!

**Models used:**
- Text: `Xenova/all-MiniLM-L6-v2` (384 dimensions, sentence-transformers)
- Image: `Xenova/clip-vit-base-patch32` (512 dimensions, CLIP vision transformer)

**For backfilling existing entities** without embeddings, use the manual tools:
```bash
# Backfill text embeddings for existing entities
python3 scripts/generate-embeddings.py

# Or use MCP tools directly
bulk_generate_embeddings(entity_ids=[...])
```

**Note**: ~20,632 entities currently have embeddings in production (legacy data may need backfill).

## GraphQL API Usage

Supabase automatically generates GraphQL types from your database schema.

### Query Examples

```graphql
# Get all collections with images
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        attributes
        entity_primary_image {
          edges {
            node {
              image_url       # Full resolution original
              thumbnail_url   # 300x300 WebP thumbnail
            }
          }
        }
      }
    }
  }
}

# Get items in a collection (via relationships)
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "collection-uuid-here"}
    }
  ) {
    edges {
      node {
        to_id
        order
        entities {  # Auto-joined by foreign key
          id
          name
          type
        }
      }
    }
  }
}

# Search entities by name (fuzzy)
query {
  entitiesCollection(
    filter: {name: {ilike: "%Charizard%"}}
  ) {
    edges {
      node {
        id
        name
        type
      }
    }
  }
}

# Query variants of an entity (using computed field)
query {
  entitiesCollection(filter: {name: {eq: "Charizard"}}) {
    edges {
      node {
        id
        name
        entity_primary_image {
          edges {
            node {
              image_url
              thumbnail_url
            }
          }
        }
        entity_variants {
          edges {
            node {
              id
              name
              attributes
              variant_primary_image {
                edges {
                  node {
                    image_url
                    thumbnail_url
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

# Query all variants directly
query {
  variantsCollection {
    edges {
      node {
        id
        name
        variant_of
        attributes
        created_at
      }
    }
  }
}

# Get variants for specific entity by ID
query {
  variantsCollection(
    filter: {variant_of: {eq: "entity-uuid-here"}}
  ) {
    edges {
      node {
        id
        name
        attributes
      }
    }
  }
}

# Query components of an entity (using computed field)
query {
  entitiesCollection(filter: {id: {eq: "megazord-uuid"}}) {
    edges {
      node {
        id
        name
        entity_components {
          edges {
            node {
              id
              name
              quantity
              order
              attributes
              component_primary_image {
                edges {
                  node {
                    image_url
                    thumbnail_url
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

# Query all components directly
query {
  componentsCollection {
    edges {
      node {
        id
        name
        component_of
        quantity
        attributes
      }
    }
  }
}

# Get components for specific entity by ID
query {
  componentsCollection(
    filter: {component_of: {eq: "entity-uuid-here"}}
  ) {
    edges {
      node {
        id
        name
        quantity
        order
      }
    }
  }
}
```

**Note**: JSONB attribute filtering (e.g., `attributes: {contains: {edition: "1st"}}`) is not supported in GraphQL. Use SQL queries for filtering by variant attributes - see Common SQL Queries section.

**API Key**: Include in headers as `apikey: sb_publishable_...` (get from `supabase status`)

## MCP Server

The database is accessible via MCP (Model Context Protocol) server for AI assistants like Claude Code.

### Features

**Read Operations (6 tools):**
- **Semantic Search**: Find collectibles using natural language
- **External ID Search**: Find entities by external system IDs (deduplication & parent lookup)
- **Entity Details**: Get complete information about items
- **Browse Collections**: Explore collection contents
- **Variants & Components**: View alternative versions and parts

**Write Operations (12 tools):**
- **Entity CRUD**: create_entity (**auto text embeddings**), update_entity, delete_entity
- **Relationships**: create_relationship, delete_relationship
- **Variants**: create_variant, update_variant
- **Components**: create_component
- **Images**: localize_image (**auto image embeddings** + thumbnail + storage), create_image (link to entity)
- **Embeddings**: generate_embedding, bulk_generate_embeddings (for backfill only - **embeddings now automatic**)

**Curator Integration (6 tools):**
- **Discovery**: list_curators, get_curator_config
- **Execution**: run_curator_fetch, validate_curator_data, get_curator_stats
- **Bulk Import**: bulk_import_curator_batch (**100x+ faster** than individual creates)
- **AI-Driven Workflows**: Claude can autonomously fetch, validate, and import collectibles data

### Multi-Environment Setup

The project supports both local and production environments through separate MCP server configurations in `.mcp.json`:

- **`database-of-things-local`** - Local Supabase (http://127.0.0.1:54321)
- **`database-of-things-prod`** - Production Supabase (requires env vars)

### Configuration

Production access requires environment variables:

```bash
# Create .env file (not committed to git)
cp .env.example .env

# Edit .env with your production credentials
export SUPABASE_PROD_URL="https://yourproject.supabase.co"
export SUPABASE_PROD_ANON_KEY="your-production-anon-key"

# Source before starting Claude Code
source .env
claude
```

### Available Tools

Once configured, you can use either environment with all 25 tools:

**Read Tools (6):**
- `search_collectibles` - Semantic search for collectibles
- `search_by_external_id` - Find entities by external_ids (for deduplication and parent lookup)
- `get_entity` - Get detailed entity information
- `browse_collection` - List items in a collection
- `get_variants` - Get entity variants
- `get_components` - Get entity components

**Write Tools (13):**
- `create_entity` (**category** parameter added), `update_entity`, `delete_entity` - Entity operations (**text embeddings auto-generated**)
- `create_relationship`, `delete_relationship` - Relationship operations
- `create_variant`, `update_variant` - Variant operations
- `create_component` - Component operations
- `localize_image` - Download image, generate thumbnail + **image embedding**, upload to Supabase storage
- `bulk_localize_images` - **Batch image localization** for existing entities (parallel processing, 10x+ faster)
- `create_image` - Link image to entity (with optional embedding)
- `generate_embedding`, `bulk_generate_embeddings` - Embedding backfill (manual only, **auto for new data**)

**Curator Tools (6):**
- `list_curators`, `get_curator_config` - Discovery
- `run_curator_fetch`, `validate_curator_data`, `get_curator_stats` - Execution
- `bulk_import_curator_batch` - **High-performance bulk import** (100x+ faster, single transaction)

**Utility Tools (1):**
- `list_categories` - Get all available category values (trading_card_games, figures, comics, video_games, buildables)

All tools are available with both local and production environment prefixes:
```
mcp__database-of-things-local__<tool_name>
mcp__database-of-things-prod__<tool_name>
```

Enable/disable servers via `/mcp` command or @mentioning in Claude Code.

**Documentation**:
- See `mcp-server/README.md` for detailed usage examples and workflow patterns
- See `docs/plans/2025-11-15-mcp-write-tools-design.md` for technical design and architecture

### Curator-MCP Integration

The MCP server's curator tools enable Claude to autonomously run curator workflows:

**New workflow (using bulk import - 100x+ faster):**
```
1. Claude uses list_curators() to discover available curators
2. Uses run_curator_fetch("Pokemon TCG") to fetch data from API (500 items)
3. Uses bulk_import_curator_batch() with all 500 items in ONE call
   - Single database transaction
   - Automatic deduplication via external_ids
   - Parallel image processing (10 concurrent downloads)
   - Automatic text/image embedding generation
   - Automatic relationship creation
4. Reports: "Imported 450 new cards in 45 seconds (450 created, 30 updated, 20 skipped)"
```

**Old workflow (for reference - deprecated but still available):**
```
1-2. Same fetch steps
3. Loop through 500 items individually:
   - search_by_external_id() → 500 MCP calls
   - create_entity() → 450 MCP calls
   - localize_image() → 450 MCP calls
   - create_relationship() → 450 MCP calls
4. Total: ~1,850 MCP calls, 10-15 minutes
```

**Performance comparison:**
| Approach | Items | Time | MCP Calls |
|----------|-------|------|-----------|
| **Bulk Import** | 500 | **~45s** | **1 call** |
| Individual | 500 | ~15 min | ~1,850 calls |
| **Speedup** | | **20x faster** | **99.9% fewer calls** |

**Note**: Embeddings (text + image) are now generated automatically - no separate embedding step needed!

This combines the power of:
- **Curator scripts** - Domain-specific data fetching and parsing
- **Bulk import function** - High-performance database operations
- **MCP tools** - Database access and parallel image processing
- **Claude's intelligence** - Error handling and workflow orchestration

For manual curator operation, use the slash commands (`/curator-run`, `/curator-init`) which provide interactive control.

## Curator System

Autonomous agents for importing collectibles data via AI-driven workflows.

**Purpose**: Make importing, updating, and reconciling collections effortless through automated fetch + intelligent MCP-based import.

### Available Commands

- `/curator:init "Collection Name"` - Initialize new curator (interactive discovery)
- `/curator:run "Collection Name"` - Execute curator to import items
- `/curator:status "Collection Name"` - Show collection stats

### Architecture (v2)

**Hybrid Design**: Python handles mechanical fetch, Claude handles intelligent import via MCP.

```
Fetch Phase:          Python script (fetch_data.py)
                      ↓
                      fetched_data.json (standardized format)
                      ↓
Import Phase:         Claude via MCP tools
                      - Semantic deduplication
                      - Entity creation
                      - Image linking
                      - Embedding generation
```

**Key Benefits**:
- ✅ Simplified fetch scripts (~200 lines vs ~500)
- ✅ Intelligent deduplication via semantic search
- ✅ Natural language invocation ("Import Pokemon Base Set")
- ✅ Multi-environment support (local vs production)

### When to Use

**Creating a curator**: Use `/curator:init "Collection Name"` when you need to import a new collection. Claude will:
- Ask Socratic questions about data source, ToS, metadata
- Generate fetch_data.py script (~200 lines)
- Create config files and secrets templates
- Test the fetch with `--limit=5`

**Running a curator**: Use `/curator:run "Collection Name"` or natural language ("Import Labubu figures"). Claude will:
- Load the run-curator skill (autonomous debugging + MCP import)
- Execute fetch_data.py
- Import via MCP tools (semantic deduplication, entity/image/relationship creation, embeddings)
- Report created/updated/failed counts

**Command variations**:
```bash
/curator:run "Labubu"                  # Full workflow
/curator:run "Labubu" --fetch-only     # Fetch only, no import
/curator:run "Labubu" --env=prod       # Use production environment
```

### Critical Principles

**1. Always load run-curator skill**: When running curators, ALWAYS load the `run-curator` skill. It contains autonomous debugging, error handling, and MCP import workflows.

**2. Multi-environment secrets**:
- `secrets.env` - Shared API keys (all environments)
- `secrets.local.env` - Local collection ID
- `secrets.prod.env` - Production collection ID

**3. Standardized fetch output**: All fetch scripts output `fetched_data.json` with format_version 1.0 (see technical reference for schema).

**4. Intelligent deduplication**: Uses MCP `search_by_external_id` for exact matching via external system IDs, with `search_collectibles` semantic fallback (0.95+ similarity threshold) when external IDs unavailable.

### Documentation

**For complete workflows and examples**: See `docs/curator-user-guide.md`
**For schemas and specifications**: See `docs/curator-technical-reference.md`

### Implementation

- Slash commands: `.claude/commands/curator-*.md`
- Skills: `.claude/skills/init-curator/` and `.claude/skills/run-curator/` (v2)
- Fetch scripts: `.curator/curators/{name}/scripts/fetch_data.py`
- Import: Claude via MCP tools (21 tools: 5 read, 11 write, 5 curator)

## Image Storage

### Storage Bucket Configuration

The `images` bucket is automatically created via migration and configured for:
- **Public read access** - Anyone can view images
- **Authenticated write** - Only authenticated users can upload/update/delete
- **File size limit** - 5MB max per image
- **Allowed types** - JPEG, PNG, GIF, WebP

### Image Optimization Strategy

**⚠️ IMPORTANT**: Supabase image transformations require **Pro Plan** ($25/month, $5 per 1,000 transforms).

**For Free Tier deployments**, use pre-generated thumbnails:

| Field | Purpose | Example |
|-------|---------|---------|
| `image_url` | Full-resolution original | `/storage/v1/object/public/images/originals/{uuid}.jpg` |
| `thumbnail_url` | 300x300 WebP thumbnail | `/storage/v1/object/public/images/thumbnails/{uuid}.webp` |

**Storage structure**:
```
images/
  originals/
    {uuid}.jpg           # Full resolution (200-500 KB)
    {uuid}.png
  thumbnails/
    {uuid}.webp          # 300x300 WebP (20-50 KB, ~90% savings)
```

**Benefits**:
- ✅ **90-95% size reduction** for list views and grids
- ✅ **$0 cost** (vs $5,000/month for 100K images × 10 views)
- ✅ **Works on Free Tier** (no Pro Plan required)
- ✅ **Instant delivery** (no on-demand processing)

### Generating Thumbnails

**For existing images** (backfill):
```bash
# If using Supabase CLI (credentials auto-detected):
./scripts/generate-all-thumbnails

# Or manually:
cd scripts/thumbnails
npm install
npm run backfill -- --dry-run  # Preview first
npm run backfill               # Process all entities
```

**Note**: If you have Supabase CLI linked (`supabase link`), credentials are auto-detected. Otherwise, create `.env` file with your credentials.

**For new uploads** (in your application):
```javascript
import { generateThumbnailFromBuffer } from './scripts/thumbnails/generate-thumbnails.js';

// Generate thumbnail when uploading
const thumbnailBuffer = await generateThumbnailFromBuffer(imageBuffer, {
  size: 300,
  quality: 85
});

// Upload both original and thumbnail
await supabase.storage.from('images').upload(`originals/${uuid}.jpg`, imageBuffer);
await supabase.storage.from('images').upload(`thumbnails/${uuid}.webp`, thumbnailBuffer);

// Create entity with both URLs
await supabase.from('entities').insert({
  id: uuid,
  name: 'Charizard',
  image_url: `/storage/v1/object/public/images/originals/${uuid}.jpg`,
  thumbnail_url: `/storage/v1/object/public/images/thumbnails/${uuid}.webp`
});
```

See `scripts/thumbnails/README.md` for detailed instructions.

### Image URL Pattern

The `image_url` and `thumbnail_url` columns store URL paths (not full URLs):

**1. Supabase Storage Paths** (recommended):
```sql
INSERT INTO entities (name, image_url, thumbnail_url)
VALUES (
  'Charizard',
  '/storage/v1/object/public/images/originals/34a6d4a2.jpg',
  '/storage/v1/object/public/images/thumbnails/34a6d4a2.webp'
);
```

**2. External URLs** (for external images without thumbnails):
```sql
INSERT INTO entities (name, image_url)
VALUES ('Charizard', 'https://images.pokemontcg.io/base1/4.png');
```

### Accessing Images

**Local development**:
```
# Original
http://127.0.0.1:54321/storage/v1/object/public/images/originals/uuid.jpg

# Thumbnail
http://127.0.0.1:54321/storage/v1/object/public/images/thumbnails/uuid.webp
```

**Production**:
```
# Original
https://yourproject.supabase.co/storage/v1/object/public/images/originals/uuid.jpg

# Thumbnail
https://yourproject.supabase.co/storage/v1/object/public/images/thumbnails/uuid.webp
```

**Image transformations** (local dev only, requires Pro Plan in production):
```
# Only works if [storage.image_transformation] enabled = true in config.toml
http://127.0.0.1:54321/storage/v1/object/public/images/uuid.png?width=300&height=400
```

### Uploading Images to Supabase Storage

**Via REST API**:
```bash
curl -X POST \
  http://127.0.0.1:54321/storage/v1/object/images/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.jpg \
  -H "apikey: your-api-key" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: image/jpeg" \
  --data-binary @charizard.jpg
```

**Via Studio UI**:
1. Open http://127.0.0.1:54323
2. Go to **Storage** in left sidebar
3. Select **images** bucket
4. Click **Upload** and select your image

**Then store the path in your entity**:
```sql
INSERT INTO entities (name, type, image_url, external_ids)
VALUES (
  'Charizard',
  'card',
  '/storage/v1/object/public/images/originals/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.jpg',
  '{"pokemontcg_io": "base1-4"}'::jsonb
);
```

### Entity Examples

**Entity (with primary image via foreign key)**:
```json
{
  "id": "uuid-here",
  "name": "Charizard",
  "type": "item",
  "category": "trading_card_games",
  "year": 1999,
  "language": "en",
  "primary_image_id": "image-uuid-here",
  "source_url": "https://pokemontcg.io/cards/base1-4",
  "name_embedding": [0.123, 0.456, ...],  // 384d vector, auto-generated
  "external_ids": {
    "pokemontcg_io": "base1-4",
    "tcgplayer": "base1-4"
  },
  "attributes": {
    "hp": 120,
    "card_number": "4/102",
    "description": "A legendary Fire-type Pokémon"
  },
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Image (stored in images table, referenced by entities)**:
```json
{
  "id": "image-uuid-here",
  "image_url": "https://images.pokemontcg.io/base1/4.png",  // or local path
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/image-uuid.webp",
  "embedding": [0.789, 0.234, ...],  // 512d CLIP vector, auto-generated
  "source_url": "https://pokemontcg.io/cards/base1-4",
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**Variant (with optional image)**:
```json
{
  "id": "variant-uuid-here",
  "variant_of": "base-entity-uuid",
  "name": "1st Edition",
  "primary_image_id": "variant-image-uuid",  // Optional, references images table
  "attributes": {
    "edition": "1st",
    "print_run": "shadowless",
    "rarity": "rare",
    "condition": "mint"
  },
  "created_at": "2024-01-15T12:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

**To create entity with image using MCP tools**:
```typescript
// 1. Create entity
const { entity_id } = await create_entity({
  name: "Charizard",
  type: "item",
  category: "trading_card_games",
  year: 1999
});

// 2. Create and link image
const { image_id } = await create_image({
  entity_id: entity_id,
  image_url: "https://images.pokemontcg.io/base1/4.png",
  is_primary: true  // Sets as primary image
});
```

## Schema Management & Migrations

Migrations are stored in `supabase/migrations/` and run automatically on `supabase start`.

**Current migrations** (chronological order):
1. `20251020000000_initial_schema.sql`: Core entities and relationships tables
2. `20251021063959_add_image_url_to_entities.sql`: Add image_url column to entities
3. `20251021064255_remove_description_from_entities.sql`: Remove description column (use attributes JSONB instead)
4. `20251021064612_convert_image_url_to_flexible_key.sql`: Rename image_url to image_key (superseded)
5. `20251021064735_create_collectible_images_bucket.sql`: Create storage bucket with policies
6. `20251021065503_rename_images_bucket.sql`: Rename bucket from collectible-images to images
7. `20251021081225_add_external_ids_to_entities.sql`: Add external_ids JSONB column with GIN index
8. `20251022165916_add_entities_with_image_urls_view.sql`: Add view for entities with image URLs
9. `20251022170207_add_image_url_generated_column.sql`: Add generated column for image URLs
10. `20251023000000_increase_graphql_page_size.sql`: Increase GraphQL default page size
11. `20251023172157_increase_graphql_page_size.sql`: (duplicate/empty - may need cleanup)
12. `20251023185803_increase_graphql_page_limit.sql`: Further increase GraphQL page limits
13. `20251023190331_add_language_and_order_columns.sql`: Add language to entities, order to relationships
14. `20251023215655_add_semantic_search_function.sql`: Add semantic search capability
15. `20251023220000_add_text_based_semantic_search.sql`: Enhanced text-based semantic search
16. `20251024191322_convert_image_key_to_image_url_paths.sql`: Convert image_key to image_url paths
17. `20251024195010_drop_relationships_attributes.sql`: **Remove attributes column from relationships**
18. `20251024195527_remove_series_attribute_from_sets.sql`: Clean up series attributes
19. `20251025164508_fix_search_by_text_image_column.sql`: Fix search functionality for images
20. `20251104233648_add_thumbnail_url.sql`: Add thumbnail_url column for pre-generated thumbnails
21. `20251105125958_add_vector_embedding.sql`: Add pgvector extension and name_embedding column for semantic search
22. `20251117140439_simplify_schema_with_enums.sql`: **Convert entities.type to entity_type enum ('item', 'collection'), drop relationships.type column**
23. `20251117153023_add_category_to_entities.sql`: **Add category_type enum and optional category column to entities (trading_card_games, figures, comics, video_games, buildables)**
24. `20251114221309_add_images_table_and_reverse_image_search.sql`: **Create images table with CLIP embeddings, join tables for additional images, reverse image search function**
25. `20251114222419_migrate_existing_images_to_images_table.sql`: **Migrate existing image_url/thumbnail_url data to images table**
26. `20251114223815_drop_old_image_columns.sql`: **Drop image_url and thumbnail_url columns from entities, variants, components**
27. `20251114223852_add_graphql_image_computed_fields.sql`: **Add GraphQL computed fields for accessing images via relationships**
28. `20251117183349_fix_search_function_signatures.sql`: **Fix search functions to use entity_type enum and match current schema**
29. `20251117193102_add_bulk_import_curator_batch.sql`: **Add bulk import function for 100x+ faster curator imports (single transaction)**
30. `20251117200000_fix_bulk_import_type_mapping.sql`: Fix entity type mapping in bulk import function
31. `20251117201000_add_hierarchical_parent_support.sql`: Add support for hierarchical parent lookups in bulk import
32. `20251119225536_drop_embedding_queue.sql`: Remove unused embedding queue table (embeddings now generated inline)
33. `20251126213601_add_image_urls_to_search_functions.sql`: Add image_url and thumbnail_url to search function results
34. `20251130194412_add_category_filter_to_search_functions.sql`: **Add category_filter parameter to semantic_search and search_by_text functions**

**To add new migrations**:
```bash
# Create new migration
./bin/supabase migration new add_feature_name

# Edit the generated file in supabase/migrations/
# Then apply with (creates automatic backup):
./scripts/safe-migrate push

# Or if you need to reset everything (requires confirmation):
./scripts/safe-migrate reset
```

**Schema versioning**: Migration files are timestamped and run in order.

**Backup Management**:
- All backups are stored in `backups/` with timestamps
- Backups are automatically created before migrations
- Use `./scripts/db-restore backups/backup_*.sql` to restore

**Migration Drift**:
If your production database has columns/features that don't exist locally:
1. Create the missing migration: `./bin/supabase migration new migration_name`
2. Write the SQL to match production (e.g., `ALTER TABLE entities ADD COLUMN ...`)
3. Apply locally: `docker exec supabase_db_database-of-things psql -U postgres -d postgres -f supabase/migrations/YYYYMMDD_migration_name.sql`
4. The migration file is now in git and new developers will get the correct schema

**Note**: Some migrations may fail with `db push` due to permission requirements (e.g., GraphQL config). Use direct psql execution as a workaround.

## Common SQL Queries

### Entity Queries

```sql
-- Find entities by type
SELECT * FROM entities WHERE type = 'collection';

-- Fuzzy name search (trigram)
SELECT * FROM entities
WHERE name % 'Charizard'  -- % is similarity operator
ORDER BY similarity(name, 'Charizard') DESC;

-- Full-text search
SELECT * FROM entities
WHERE to_tsvector('english', name)
      @@ to_tsquery('english', 'pokemon & card');

-- Query JSONB attributes
SELECT * FROM entities
WHERE attributes @> '{"hp": 120}';

-- Query external_ids (separate JSONB column)
SELECT * FROM entities
WHERE external_ids @> '{"tcgplayer": "base1-4"}';

-- Extract JSONB values and standard columns (e.g., for trading cards)
SELECT e.name, i.image_url, i.thumbnail_url,
       e.attributes->>'hp' as hp,
       e.external_ids->>'pokemontcg_io' as tcg_id
FROM entities e
LEFT JOIN images i ON e.primary_image_id = i.id
WHERE e.category = 'trading_card_games';

-- Find entities missing thumbnails (for backfill)
SELECT e.id, e.name, i.image_url
FROM entities e
JOIN images i ON e.primary_image_id = i.id
WHERE i.thumbnail_url IS NULL;

-- Find entities missing embeddings (for backfill)
SELECT id, name, type
FROM entities
WHERE name_embedding IS NULL
LIMIT 100;

-- Semantic search using text (with category filter)
SELECT id, name, type, category, similarity
FROM search_by_text('fire dragon pokemon', 'item', 'trading_card_games', 20);

-- Semantic search using vector (requires pre-computed embedding)
SELECT id, name, type, category, similarity
FROM semantic_search('[0.1, 0.2, ...]'::vector(384), NULL, NULL, 10);
```

### Relationship Queries

```sql
-- Get all items in a collection (parent → child)
SELECT e.*
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid-here';

-- Get what contains an item (reverse: child → parent)
SELECT e.*
FROM entities e
JOIN relationships r ON r.from_id = e.id
WHERE r.to_id = 'item-uuid-here';

-- Relationship with order column
SELECT e.*, r."order" as position
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid'
ORDER BY r."order";

-- Traverse full hierarchy (franchise → game → collection → card)
WITH RECURSIVE hierarchy AS (
  -- Start with a franchise
  SELECT id, name, type, 0 as level
  FROM entities
  WHERE name = 'Pokémon'

  UNION ALL

  -- Recursively get all contained items
  SELECT e.id, e.name, e.type, h.level + 1
  FROM entities e
  JOIN relationships r ON r.to_id = e.id
  JOIN hierarchy h ON r.from_id = h.id
)
SELECT * FROM hierarchy ORDER BY level, name;

-- Get all variants of a base entity
SELECT v.*
FROM variants v
WHERE v.variant_of = 'base-entity-uuid';

-- Get variant count per entity
SELECT e.id, e.name, COUNT(v.id) as variant_count
FROM entities e
LEFT JOIN variants v ON v.variant_of = e.id
GROUP BY e.id, e.name
HAVING COUNT(v.id) > 0
ORDER BY variant_count DESC;

-- Find variants with specific attributes
SELECT v.*, e.name as base_name
FROM variants v
JOIN entities e ON v.variant_of = e.id
WHERE v.attributes @> '{"edition": "1st"}'::jsonb;

-- Get entity with all its variants (JSON aggregation)
SELECT
  e.id,
  e.name,
  json_agg(
    json_build_object(
      'id', v.id,
      'name', v.name,
      'attributes', v.attributes
    )
  ) FILTER (WHERE v.id IS NOT NULL) as variants
FROM entities e
LEFT JOIN variants v ON v.variant_of = e.id
WHERE e.id = 'entity-uuid-here'
GROUP BY e.id, e.name;

-- Get all components for an item (ordered)
SELECT * FROM components
WHERE component_of = 'item-uuid'
ORDER BY COALESCE("order", 999999), name;

-- Check if item has all required components (with quantities)
SELECT name, quantity
FROM components
WHERE component_of = 'item-uuid'
ORDER BY COALESCE("order", 999999), name;

-- Get component count per entity
SELECT e.id, e.name, COUNT(c.id) as component_count
FROM entities e
LEFT JOIN components c ON c.component_of = e.id
GROUP BY e.id, e.name
HAVING COUNT(c.id) > 0
ORDER BY component_count DESC;

-- Find components with specific attributes
SELECT c.*, e.name as parent_name
FROM components c
JOIN entities e ON c.component_of = e.id
WHERE c.attributes @> '{"material": "plastic"}'::jsonb;

-- Get entity with all its components (JSON aggregation)
SELECT
  e.id,
  e.name,
  json_agg(
    json_build_object(
      'id', c.id,
      'name', c.name,
      'quantity', c.quantity,
      'order', c.order
    )
  ) FILTER (WHERE c.id IS NOT NULL) as components
FROM entities e
LEFT JOIN components c ON c.component_of = e.id
WHERE e.id = 'entity-uuid-here'
GROUP BY e.id, e.name;
```

## Configuration

### supabase/config.toml

Key settings:
- **Analytics**: Disabled (`[analytics] enabled = false`) to avoid Docker socket issues
- **API Port**: 54321
- **DB Port**: 54322
- **Studio Port**: 54323
- **GraphQL**: Auto-enabled via `graphql_public` schema

## Troubleshooting

**Issue**: Supabase won't start, vector container errors
**Solution**: Analytics is already disabled in config.toml. If issues persist, check Docker socket permissions.

**Issue**: Database connection refused
**Solution**: Wait for health checks. Run `./bin/supabase status` to check if all services are healthy.

**Issue**: GraphQL not showing my tables
**Solution**: Tables must be in `public` schema. Run `\dt` in psql to verify.

**Issue**: Can't upload images
**Solution**: Create storage bucket first in Studio UI or via SQL.

## Important Notes

- **UUIDs**: All primary keys are UUIDs generated by PostgreSQL (`uuid_generate_v4()`)
- **Cascade Deletes**: Relationships cascade when entities are deleted
- **Unique Relationships**: Cannot create duplicate relationships between same entities with same type
- **JSONB Performance**: GIN indexes support fast JSONB queries, but avoid queries that scan entire JSONB objects
- **Local Only**: Current setup is for local development. For production, deploy to Supabase Cloud or self-host.
- **API Keys**: Local development uses test keys. Never commit production keys to git.
- **Supabase CLI**: Located in `./bin/supabase` (downloaded binary, not globally installed)
