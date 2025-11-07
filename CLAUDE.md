# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal, pure graph database for managing collectibles using PostgreSQL via Supabase. The architecture is intentionally simple: just entities and relationships with JSONB attributes for flexibility.

**Core Philosophy**: Everything is an entity (collections, items, variants, etc.), connected by typed relationships. No fixed schema beyond the essentials.

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

The safe-migrate wrapper:
- ✅ **Automatically creates backups** before any migration
- ✅ **Prevents accidental data loss** with confirmation prompts
- ✅ **Makes recovery trivial** if something goes wrong
- ✅ **Stores timestamped backups** in `backups/`

**Why this matters:**
- `./bin/supabase db reset` **DESTROYS ALL DATA** without warning
- `./scripts/safe-migrate reset` creates a backup first and requires explicit confirmation
- Even `./scripts/safe-migrate push` creates a backup before applying migrations

**Recovery from disaster:**
```bash
# List available backups
ls -lh backups/

# Restore from most recent backup
./scripts/db-restore backups/backup_YYYYMMDD_HHMMSS.sql
```

**Direct supabase commands (USE WITH CAUTION):**
```bash
# Only use these if you know what you're doing
./bin/supabase db push    # Apply migrations without backup
./bin/supabase db reset   # DESTROYS ALL DATA - avoid at all costs!
```

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

The schema consists of only two tables:

**`entities`** - Everything in the system (collections, items, variants, components):
- `id` (UUID): Primary key
- `type` (TEXT): Entity type (e.g., "collection", "card", "figure")
- `name` (TEXT): Display name
- `year` (INT): Optional universal year attribute
- `country` (CHAR(2)): Optional ISO country code
- `language` (CHAR(2)): Optional ISO 639-1 language code (e.g., "en", "ja", "es")
- `image_url` (TEXT): Image URL path - local storage uses `/storage/v1/object/public/images/originals/uuid.ext`, external URLs stored as-is
- `thumbnail_url` (TEXT): Optional pre-generated thumbnail path (typically 300x300 WebP) - `/storage/v1/object/public/images/thumbnails/uuid.webp`
- `name_embedding` (vector(384)): Vector embedding for semantic search (nullable, generated externally)
- `external_ids` (JSONB): External system IDs (e.g., `{"tcgplayer": "base1-4", "pokemontcg_io": "base1-4"}`)
- `attributes` (JSONB): All other data (description, additional images, custom fields)
- Timestamps: `created_at`, `updated_at`

**`relationships`** - Connections between entities:
- `id` (UUID): Primary key
- `from_id` (UUID): Source entity
- `to_id` (UUID): Target entity
- `type` (TEXT): Relationship type (e.g., "contains", "variant_of", "component_of")
- `order` (INT): Sort order for items in collections (nullable)
- `created_at` timestamp
- UNIQUE constraint on `(from_id, to_id, type)`
- **Note**: Previously had an `attributes` JSONB column, but it was removed in migration `20251024195010_drop_relationships_attributes.sql` as it was unused (all values were empty objects)

### Design Patterns

**JSONB Attributes Philosophy**:
- Only universally applicable fields are columns (`name`, `type`, `year`, `country`, `language`, `image_url`, `thumbnail_url`)
- External system IDs are stored in dedicated `external_ids` JSONB column (not in `attributes`)
- For relationships, commonly-used fields like `order` are dedicated columns
- Everything else goes in `attributes` JSONB (description, additional images, custom metadata)
- Allows heterogeneous entity types without schema changes
- **Important**: Always use dedicated columns when available instead of JSONB attributes
- **Relationships**: The `relationships` table has NO attributes column - all relationship metadata must use dedicated columns (currently only `order` exists)

**Relationship Types** (all use parent→child direction):
- `contains`: Parent contains child (e.g., Collection → Card, Franchise → Game)
  - Most common relationship type
  - Makes querying intuitive: "show me what this collection contains"
- `variant_of`: Variant → Base (e.g., "Shadowless Charizard" → "Charizard")
  - For alternative versions of the same item
- `part_of`: Component → Whole (e.g., "Megazord arm" → "Megazord")
  - For physical components or pieces
- Custom types as needed for domain-specific relationships

**Graph Traversal**:
- Use `from_id + type` for forward traversal (what does this entity contain/relate to?)
- Use `to_id + type` for reverse traversal (what contains/relates to this entity?)
- Indexes optimized for both directions

### PostgreSQL Extensions

- **uuid-ossp**: UUID generation (`uuid_generate_v4()`)
- **pg_trgm**: Trigram similarity for fuzzy name matching
- **vector**: pgvector extension for vector embeddings and similarity search (cosine distance, HNSW indexing)

### Indexes

**Entity lookups**:
- `idx_entities_type`: Filter by entity type
- `idx_entities_name`: Exact name lookup
- `idx_entities_name_trgm`: Fuzzy name search (GIN trigram)
- `idx_entities_name_embedding`: Semantic search (HNSW with cosine distance)
- `idx_entities_language`: Filter by language (partial index, only non-null values)
- `idx_entities_attributes`: JSONB path queries on attributes (GIN)
- `idx_entities_external_ids`: JSONB queries on external_ids (GIN)
- `idx_entities_search`: Full-text search on name

**Relationship traversal**:
- `idx_relationships_from_type`: Outbound relationships by type
- `idx_relationships_to_type`: Inbound relationships by type
- `idx_relationships_order`: Sort by order (partial index, only non-null values)

## Semantic Search

The database supports semantic search using vector embeddings, allowing you to find similar entities based on meaning rather than exact text matches.

### How It Works

1. **Embeddings**: Entity names are converted to 384-dimensional vectors using a sentence-transformer model (e.g., `all-MiniLM-L6-v2`)
2. **Storage**: Vectors stored in `name_embedding` column
3. **Indexing**: HNSW (Hierarchical Navigable Small World) index enables fast approximate nearest neighbor search
4. **Similarity**: Uses cosine distance (1 - cosine similarity) to find semantically similar entities

### Search Functions

**`semantic_search(query_embedding, entity_type_filter, result_limit)`** - Vector-based search:
```sql
-- Search using a pre-computed embedding vector
SELECT * FROM semantic_search(
  '[0.123, 0.456, ...]'::vector(384),  -- Your query embedding
  'card',                                -- Optional: filter by type
  20                                     -- Limit results
);
```

**`search_by_text(query_text, entity_type_filter, result_limit)`** - Text-based search:
```sql
-- Search using plain text (finds closest entity name, uses its embedding)
SELECT * FROM search_by_text(
  'fire dragon pokemon',  -- Plain text query
  'card',                 -- Optional: filter by type
  20                      -- Limit results
);
```

### GraphQL Examples

```graphql
# Semantic search with vector embedding
query {
  semantic_search(
    args: {
      query_embedding: "[0.123, 0.456, ...]"
      entity_type_filter: "card"
      result_limit: 20
    }
  ) {
    id
    name
    type
    similarity
    image_url
    thumbnail_url
  }
}

# Text-based semantic search
query {
  search_by_text(
    args: {
      query_text: "fire dragon pokemon"
      entity_type_filter: "card"
      result_limit: 20
    }
  ) {
    id
    name
    type
    similarity
  }
}
```

### Generating Embeddings

Embeddings must be generated externally using Python or another language:

```python
from sentence_transformers import SentenceTransformer

# Load model (384 dimensions)
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Generate embedding
entity_name = "Charizard"
embedding = model.encode(entity_name).tolist()

# Store in database
supabase.table('entities').update({
    'name_embedding': embedding
}).eq('id', entity_id).execute()
```

**Note**: ~20,632 entities currently have embeddings in production.

## GraphQL API Usage

Supabase automatically generates GraphQL types from your database schema.

### Query Examples

```graphql
# Get all collections with thumbnails
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        image_url       # Full resolution original
        thumbnail_url   # 300x300 WebP thumbnail
        attributes
      }
    }
  }
}

# Get items in a collection (via relationships)
query {
  relationshipsCollection(
    filter: {
      from_id: {eq: "collection-uuid-here"}
      type: {eq: "contains"}
    }
  ) {
    edges {
      node {
        to_id
        attributes
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
```

**API Key**: Include in headers as `apikey: sb_publishable_...` (get from `supabase status`)

## Curator System

Autonomous agents for importing collectibles data, implemented as project-level slash commands and skills.

### Available Commands

- `/curator:init "Collection Name"` - Initialize new curator (interactive discovery)
- `/curator:run "Collection Name"` - Execute curator to import items
- `/curator:status "Collection Name"` - Show collection stats

### Example Usage

```bash
# Create curator
/curator:init "Pokemon TCG"
# → Interactive questions about collection and data sources
# → Generates plan and scripts in .curator/curators/Pokemon TCG/

# Run curator
/curator:run "Pokemon TCG"
# → Executes fetch and import scripts autonomously
# → Fixes errors, installs dependencies
# → Reports: "Imported 152 cards from pokemontcg.io"

# Check status
/curator:status "Pokemon TCG"
# → Collection: 152 cards, last updated 2 hours ago
```

### How It Works

1. **Discovery** (`/curator:init`) - Invokes `init-curator` skill for Socratic questioning, generates import plan and working scripts
2. **Execution** (`/curator:run`) - Invokes `run-curator` skill to autonomously run scripts, debugging and fixing issues
3. **Results** - Reports imported items and issues resolved

**Implementation**:
- Slash commands: `.claude/commands/curator-*.md`
- Skills: `.claude/skills/init-curator/` and `.claude/skills/run-curator/`
- Generated curators: `.curator/curators/{name}/scripts/`

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

**Using external URL** (no thumbnail):
```json
{
  "id": "uuid-here",
  "name": "Charizard",
  "type": "card",
  "year": 1999,
  "language": "en",
  "image_url": "https://images.pokemontcg.io/base1/4.png",
  "thumbnail_url": null,
  "external_ids": {
    "pokemontcg_io": "base1-4",
    "tcgplayer": "base1-4"
  },
  "attributes": {
    "hp": 120,
    "card_number": "4/102",
    "description": "A legendary Fire-type Pokémon"
  }
}
```

**Using Supabase Storage** (with thumbnail):
```json
{
  "id": "34a6d4a2-50d6-459e-9ae8-f29271f0e16d",
  "name": "Blastoise",
  "type": "card",
  "year": 1999,
  "language": "en",
  "image_url": "/storage/v1/object/public/images/originals/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.webp",
  "external_ids": {
    "pokemontcg_io": "base1-2"
  },
  "attributes": {
    "hp": 100,
    "card_number": "2/102",
    "description": "A powerful Water-type Pokémon",
    "images": [
      "/storage/v1/object/public/images/originals/34a6d4a2-front.jpg",
      "/storage/v1/object/public/images/originals/34a6d4a2-back.jpg"
    ]
  }
}
```

### Production Deployment

No special configuration needed - just update your application's base URL from development (`http://127.0.0.1:54321`) to production (`https://yourproject.supabase.co`).

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

-- Extract JSONB values and standard columns
SELECT name, image_url, thumbnail_url,
       attributes->>'hp' as hp,
       external_ids->>'pokemontcg_io' as tcg_id
FROM entities
WHERE type = 'card';

-- Find entities missing thumbnails (for backfill)
SELECT id, name, image_url
FROM entities
WHERE image_url IS NOT NULL
  AND thumbnail_url IS NULL;

-- Find entities missing embeddings (for backfill)
SELECT id, name, type
FROM entities
WHERE name_embedding IS NULL
LIMIT 100;

-- Semantic search using text
SELECT id, name, type, similarity
FROM search_by_text('fire dragon pokemon', 'card', 20);

-- Semantic search using vector (requires pre-computed embedding)
SELECT id, name, type, similarity
FROM semantic_search('[0.1, 0.2, ...]'::vector(384), NULL, 10);
```

### Relationship Queries

```sql
-- Get all items in a collection (parent → child)
SELECT e.*
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid-here'
  AND r.type = 'contains';

-- Get what contains an item (reverse: child → parent)
SELECT e.*
FROM entities e
JOIN relationships r ON r.from_id = e.id
WHERE r.to_id = 'item-uuid-here'
  AND r.type = 'contains';

-- Get all variants of a base item (variants point to base)
SELECT e.*
FROM entities e
JOIN relationships r ON r.from_id = e.id
WHERE r.to_id = 'base-item-uuid'
  AND r.type = 'variant_of';

-- Relationship with order column
SELECT e.*, r."order" as position
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid'
  AND r.type = 'contains'
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
  WHERE r.type = 'contains'
)
SELECT * FROM hierarchy ORDER BY level, name;
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
