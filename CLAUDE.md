# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

A minimal, pure graph database for managing collectibles using PostgreSQL via Supabase. Everything is an entity (collections, items) connected by relationships with JSONB attributes for flexibility.

**Mission**: Build the most comprehensive collectibles database on the Internet.

**Core Philosophy**:
- Pure graph model for maximum flexibility (many-to-many relationships, arbitrary nesting)
- Minimal metadata by design - focus on coverage and relationships over exhaustive details
- Source attribution via `source_url` and `external_ids` for data provenance
- Automated curator system for imports, updates, and reconciliation

**Not optimizing for**:
- Exhaustive metadata (that's what source links are for)
- Real-time market data (we're a catalog, not a marketplace)
- User-generated content (curators maintain data quality)

## Development Commands

### Supabase Local Development

```bash
./bin/supabase start    # Start full stack (PostgreSQL, Auth, Storage, GraphQL, Studio)
./bin/supabase stop     # Stop all services
./bin/supabase status   # Check status and get API keys
./bin/supabase logs     # View logs
```

### Database Operations

```bash
# Access PostgreSQL CLI
docker exec -it supabase_db_database-of-things psql -U postgres -d postgres

# Migrations (ALWAYS use safe-migrate for automatic backups)
./bin/supabase migration new migration_name    # Create migration
./scripts/safe-migrate push                    # Apply (creates backup)
./scripts/safe-migrate reset                   # Reset (requires confirmation)
./bin/supabase db diff -f migration_name       # Generate migration from changes

# Backup/Restore
./scripts/db-backup
./scripts/db-restore backups/backup_YYYYMMDD_HHMMSS.sql
./scripts/storage-backup                       # Backup images bucket
./scripts/storage-restore backups/storage_*.tar.gz
```

**CRITICAL**: Always use `./scripts/safe-migrate` instead of `./bin/supabase db` commands. Direct `db reset` destroys all data without warning.

### Testing

```bash
# SQL schema tests (requires running Supabase)
bash tests/run-all-tests.sh
```

### MCP Server (TypeScript)

```bash
cd mcp-server && npm install    # Install dependencies
npm run build                   # Compile TypeScript → build/
npm run watch                   # Watch mode during development
```

### Data Seeding

```bash
python3 scripts/seed-sample-data.py    # Seed with 24 entities, 6 variants
```

Seeded data includes 4 top-level collections (Pokemon TCG, Power Rangers, Marvel Comics, Video Games), 16 items, 6 variants, all with embeddings.

## Supabase Stack Access

When running (`./bin/supabase start`):

- **Studio UI**: http://127.0.0.1:54323 - Visual database editor, SQL editor
- **GraphQL API**: http://127.0.0.1:54321/graphql/v1
- **REST API**: http://127.0.0.1:54321/rest/v1
- **Storage API**: http://127.0.0.1:54321/storage/v1
- **Database**: postgresql://postgres:postgres@127.0.0.1:54322/postgres

API keys shown when you run `./bin/supabase status` (local dev keys only).

## Database Schema

### Tables

**`entities`** - Collections and items:
- `id` (UUID): Primary key
- `type` (entity_type ENUM): 'item' or 'collection'
- `category` (category_type ENUM): trading_card_games, figures, comics, video_games, buildables (nullable)
- `name` (TEXT): Display name
- `year` (INT): Optional year
- `country` (CHAR(2)): Optional ISO country code
- `language` (CHAR(2)): Optional ISO 639-1 language code
- `primary_image_id` (UUID): FK to images table
- `source_url` (TEXT): Source page URL for attribution
- `name_embedding` (vector(384)): Auto-generated for semantic search
- `external_ids` (JSONB): External system IDs (e.g., `{"tcgplayer": "base1-4", "pokemontcg_io": "base1-4"}`)
- `attributes` (JSONB): All other metadata (description, custom fields)
- `created_at`, `updated_at` timestamps

**`images`** - Unified image storage with embeddings:
- `id` (UUID): Primary key
- `image_url` (TEXT): Path like `/storage/v1/object/public/images/originals/uuid.jpg` or external URL
- `thumbnail_url` (TEXT): 300x300 WebP thumbnail path
- `embedding` (vector(512)): CLIP embedding for reverse image search (auto-generated)
- `source_url` (TEXT): Attribution URL
- `created_at`, `updated_at` timestamps

**`relationships`** - Entity connections (parent→child "contains"):
- `id` (UUID): Primary key
- `from_id` (UUID): Parent entity
- `to_id` (UUID): Child entity
- `order` (INT): Sort order (nullable)
- UNIQUE constraint on `(from_id, to_id)`

**`variants`** - Alternative versions (1st Edition, Shadowless, Holofoil):
- `id` (UUID): Primary key
- `variant_of` (UUID): FK to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Variant name
- `primary_image_id` (UUID): FK to images
- `attributes` (JSONB): Variant metadata (edition, print run, rarity, condition)

**`components`** - Physical pieces (Zord parts, game tokens):
- `id` (UUID): Primary key
- `component_of` (UUID): FK to entities (NOT NULL, CASCADE delete)
- `name` (TEXT): Component name
- `quantity` (INT): Default 1
- `order` (INT): Sort order
- `primary_image_id` (UUID): FK to images
- `attributes` (JSONB): Component metadata

**Join tables**: `entity_additional_images`, `variant_additional_images`, `component_additional_images` for multiple images per item.

### Key Design Patterns

**Images Architecture**:
- All images in single `images` table, referenced via `primary_image_id` FK
- Additional images via join tables with optional `order`
- 512d CLIP embeddings auto-generated for reverse image search
- URL pattern: `/storage/v1/object/public/images/{originals|thumbnails}/uuid.{ext}`
- Access via GraphQL computed fields: `entity_primary_image()`, `entity_additional_images()`

**JSONB Philosophy**:
- Only universal fields are columns (`name`, `type`, `year`, `country`, `language`)
- External IDs in dedicated `external_ids` column (NOT in `attributes`)
- Everything else in `attributes` JSONB
- Always use dedicated columns when available

**Relationships**:
- All represent "contains" semantic (Collection → Card, Franchise → Game)
- Use `from_id` for forward traversal (what does this contain?)
- Use `to_id` for reverse traversal (what contains this?)
- For variants/components, use dedicated tables instead of relationships

**Cascade Behavior**:
- Variants auto-delete when base entity deleted
- Components auto-delete when parent entity deleted
- Relationships cascade when entities deleted

### PostgreSQL Extensions

- `uuid-ossp` - UUID generation (`uuid_generate_v4()`)
- `pg_trgm` - Trigram similarity for fuzzy name matching
- `vector` - pgvector for embeddings (HNSW indexing, cosine distance)

### Key Indexes

- `idx_entities_type`, `idx_entities_category` - Filter by type/category
- `idx_entities_name_trgm` - Fuzzy name search (GIN trigram)
- `idx_entities_name_embedding` - Semantic search (HNSW cosine)
- `idx_entities_external_ids` - JSONB queries on external_ids (GIN)
- `idx_relationships_from_id`, `idx_relationships_to_id` - Graph traversal
- `idx_images_embedding` - Reverse image search (HNSW cosine)

## Semantic Search

Embeddings auto-generated when creating entities/images via MCP tools.

**Models**:
- Text: `Xenova/all-MiniLM-L6-v2` (384d sentence-transformers)
- Image: `Xenova/clip-vit-base-patch32` (512d CLIP)

**Use MCP `entity_search` for semantic search** - handles synonyms and variations properly ("and" vs "&", "pokemon" vs "pokémon").

```sql
-- SQL functions available but have limitations (trigram matching first)
SELECT * FROM search_by_text('fire dragon pokemon', 'item', 'trading_card_games', 20);
SELECT * FROM semantic_search('[0.1, ...]'::vector(384), 'item', NULL, 10);
```

**Categories**: `trading_card_games`, `figures`, `comics`, `video_games`, `buildables`

For backfilling existing entities: `python3 scripts/generate-embeddings.py`

## GraphQL API

Supabase auto-generates GraphQL from schema. Include `apikey` header (from `supabase status`).

```graphql
# Get collections with images
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        entity_primary_image {
          edges { node { image_url, thumbnail_url } }
        }
      }
    }
  }
}

# Get items in a collection
query {
  relationshipsCollection(filter: {from_id: {eq: "uuid"}}) {
    edges {
      node {
        to_id
        order
        entities { id, name, type }
      }
    }
  }
}
```

**Note**: JSONB attribute filtering not supported in GraphQL. Use SQL for that.

See `docs/graphql-examples.md` for more examples.

## MCP Server

Database accessible via MCP tools for both local and production environments. Built on `@modelcontextprotocol/sdk@^1.29.0` using proper MCP primitives: Tools, Resources, and Prompts.

### Tools (16 total)

**Entity (6)**:
- `entity_search` - Semantic search (recommended for discovery)
- `entity_find` - Exact lookup by external ID (deduplication)
- `entity_get` - Full entity details with parents, children, variants, components
- `entity_create`, `entity_update`, `entity_delete` - CRUD (create auto-generates text embedding)

**Bulk (1)**:
- `entities_upsert` - Bulk upsert into a collection: single transaction, deduplication via `external_ids`, parallel image processing, auto embeddings. Use for all curator imports.

**Collections & Relationships (3)**:
- `collection_browse` - List items inside a collection
- `relationship_create`, `relationship_delete` - Parent→child graph edges

**Variants & Components (5)**:
- `variant_list`, `variant_create`, `variant_update`
- `component_list`, `component_create`

**Images (1)**:
- `image_localize` - Download external image, generate thumbnail + CLIP embedding, upload to Supabase Storage, link to entity

### Resources

Curator specs are exposed as MCP Resources at `curator://{name}`:

```
curator://Pokemon TCG    # Returns config.json, prompt.md, collection IDs
```

List all curators: read the `curator://` resource list.

### Prompts

`run_curator(name, env, instructions?)` — fuzzy-matches a curator name and returns a ready-to-execute protocol injected with that curator's spec and collection ID.

### Environment Prefixes

```
mcp__database-of-things-local__<tool>   # Local Supabase
mcp__database-of-things-prod__<tool>    # Production
```

### Production Setup

```bash
cp .env.example .env
# Edit with SUPABASE_PROD_URL and SUPABASE_PROD_ANON_KEY
source .env && claude
```

### Bulk Import Workflow

```
entities_upsert(collection_id, items) → ONE call handles all:
  - Single DB transaction via import_curator_batch RPC
  - Auto deduplication via external_ids
  - Parallel image processing (configurable concurrency)
  - Auto text embeddings for new entities
  Result: { created, updated, skipped, errors } in ~45s for 500 items
```

## Curator System

Autonomous agents for importing collectibles data.

### Slash Commands (Claude Code)

- `/curator:init "Name"` - Initialize new curator (interactive discovery)
- `/curator:run "Name"` - Execute curator import
- `/curator:status "Name"` - Show collection stats

### Curator Structure

```
.curator/specs/<Name>/
├── config.json           # type: "agent", collection metadata, dedup strategy
├── prompt.md             # Instructions: sources, scope, hierarchy, exclusions
├── secrets.local.env     # Local COLLECTION_ID
└── secrets.prod.env      # Production COLLECTION_ID
```

**Deduplication**: Uses `external_ids` for exact matching, semantic fallback (0.95+ similarity) when external IDs unavailable.


## Image Storage

Images in Supabase Storage bucket `images/`:
- `originals/{uuid}.jpg` - Full resolution (200-500 KB)
- `thumbnails/{uuid}.webp` - 300x300 WebP (20-50 KB, ~90% savings)

**Use `image_localize` MCP tool** - handles download, thumbnail generation, CLIP embedding, and storage upload automatically.

**Bucket config**: Public read, authenticated write, 5MB max, JPEG/PNG/GIF/WebP.

**Accessing**:
```
# Local
http://127.0.0.1:54321/storage/v1/object/public/images/originals/uuid.jpg

# Production
https://yourproject.supabase.co/storage/v1/object/public/images/originals/uuid.jpg
```

See `docs/images.md` for detailed documentation.

## Common SQL Queries

```sql
-- Find entities by type
SELECT * FROM entities WHERE type = 'collection';

-- Fuzzy name search
SELECT * FROM entities WHERE name % 'Charizard' ORDER BY similarity(name, 'Charizard') DESC;

-- Query external_ids
SELECT * FROM entities WHERE external_ids @> '{"tcgplayer": "base1-4"}';

-- Get items in collection
SELECT e.* FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid';

-- Get variants
SELECT v.* FROM variants v WHERE v.variant_of = 'entity-uuid';
```

See `docs/sql-examples.md` for comprehensive query examples.

## Schema Management

Migrations in `supabase/migrations/`, run automatically on `supabase start`.

```bash
./bin/supabase migration new feature_name    # Create
./scripts/safe-migrate push                  # Apply (auto backup)
./bin/supabase migration list --linked       # Check status
```

**Never**: Apply migrations via Dashboard SQL Editor, use direct psql for schema changes, skip creating migration files.

See `docs/migrations.md` for full migration list and tracking.

## Configuration

### supabase/config.toml

- Analytics disabled (`[analytics] enabled = false`) - avoids Docker socket issues
- Ports: API 54321, DB 54322, Studio 54323
- GraphQL auto-enabled via `graphql_public` schema

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Supabase won't start | Check Docker socket permissions, analytics already disabled |
| Database connection refused | Wait for health checks, run `./bin/supabase status` |
| GraphQL not showing tables | Tables must be in `public` schema, run `\dt` in psql |
| Can't upload images | Create storage bucket first in Studio |

## Important Notes

- All primary keys are UUIDs via `uuid_generate_v4()`
- Relationships cascade delete when entities deleted
- Unique constraint prevents duplicate relationships
- GIN indexes for fast JSONB queries (avoid full-object scans)
- Local dev only - for production, deploy to Supabase Cloud
- Supabase CLI at `./bin/supabase` (local binary, not global)
- Never commit production keys to git

## Reference Documentation

- **Migrations**: `docs/migrations.md` - Full list and tracking
- **GraphQL**: `docs/graphql-examples.md` - Query examples
- **SQL**: `docs/sql-examples.md` - Common queries
- **Images**: `docs/images.md` - Storage and thumbnails
- **Curator specs**: `.curator/specs/<Name>/prompt.md` — each curator's data source and import instructions
- **MCP Server**: `mcp-server/src/` — Tools in `tools/`, Resources in `resources/`, Prompts in `prompts/`
