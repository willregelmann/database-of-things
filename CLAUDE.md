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
- `image_url` (TEXT): Image URL path - local storage uses `/storage/v1/object/public/images/uuid.ext`, external URLs stored as-is
- `attributes` (JSONB): All other data (description, additional images, external IDs, custom fields)
- Timestamps: `created_at`, `updated_at`

**`relationships`** - Connections between entities:
- `id` (UUID): Primary key
- `from_id` (UUID): Source entity
- `to_id` (UUID): Target entity
- `type` (TEXT): Relationship type (e.g., "contains", "variant_of", "component_of")
- `order` (INT): Sort order for items in collections (nullable)
- `attributes` (JSONB): Relationship-specific data (additional metadata)
- `created_at` timestamp
- UNIQUE constraint on `(from_id, to_id, type)`

### Design Patterns

**JSONB Attributes Philosophy**:
- Only universally applicable fields are columns (`name`, `type`, `year`, `country`, `language`, `image_url`)
- For relationships, commonly-used fields like `order` are dedicated columns
- Everything else goes in `attributes` JSONB (additional images, external IDs, custom metadata)
- Allows heterogeneous entity types without schema changes
- **Important**: Always use dedicated columns when available instead of JSONB attributes

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

### Indexes

**Entity lookups**:
- `idx_entities_type`: Filter by entity type
- `idx_entities_name`: Exact name lookup
- `idx_entities_name_trgm`: Fuzzy name search (GIN trigram)
- `idx_entities_language`: Filter by language
- `idx_entities_image_url`: Image URL lookups (partial index, only non-null values)
- `idx_entities_attributes`: JSONB path queries (GIN)
- `idx_entities_search`: Full-text search on name

**Relationship traversal**:
- `idx_relationships_from_type`: Outbound relationships by type
- `idx_relationships_to_type`: Inbound relationships by type
- `idx_relationships_order`: Sort by order
- `idx_relationships_attributes`: JSONB queries on relationship data

## GraphQL API Usage

Supabase automatically generates GraphQL types from your database schema.

### Query Examples

```graphql
# Get all collections
query {
  entitiesCollection(filter: {type: {eq: "collection"}}) {
    edges {
      node {
        id
        name
        image_url
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

## Image Storage

### Storage Bucket Configuration

The `images` bucket is automatically created via migration and configured for:
- **Public read access** - Anyone can view images
- **Authenticated write** - Only authenticated users can upload/update/delete
- **File size limit** - 5MB max per image
- **Allowed types** - JPEG, PNG, GIF, WebP

### Image URL Pattern

The `image_url` column stores URL paths (not full URLs) using two patterns:

**1. Supabase Storage Paths** (recommended):
```sql
INSERT INTO entities (name, image_url)
VALUES ('Charizard', '/storage/v1/object/public/images/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.png');
```

**2. External URLs** (for external images):
```sql
INSERT INTO entities (name, image_url)
VALUES ('Charizard', 'https://images.pokemontcg.io/base1/4.png');
```

### Accessing Images

**Local development**:
```
http://127.0.0.1:54321/storage/v1/object/public/images/uuid.png
```

**Production**:
```
https://yourproject.supabase.co/storage/v1/object/public/images/uuid.png
```

**With transformations** (resize, format, quality):
```
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
INSERT INTO entities (name, type, image_url)
VALUES ('Charizard', 'card', '/storage/v1/object/public/images/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.jpg');
```

### Entity Examples

**Using external URL**:
```json
{
  "id": "uuid-here",
  "name": "Charizard",
  "type": "card",
  "image_url": "https://images.pokemontcg.io/base1/4.png",
  "attributes": {
    "hp": 120,
    "card_number": "4/102"
  }
}
```

**Using Supabase Storage**:
```json
{
  "id": "uuid-here",
  "name": "Blastoise",
  "type": "card",
  "image_url": "/storage/v1/object/public/images/34a6d4a2-50d6-459e-9ae8-f29271f0e16d.jpg",
  "attributes": {
    "hp": 100,
    "card_number": "2/102",
    "images": [
      "/storage/v1/object/public/images/34a6d4a2-front.jpg",
      "/storage/v1/object/public/images/34a6d4a2-back.jpg"
    ]
  }
}
```

### Production Deployment

No special configuration needed - just update your application's base URL from development (`http://127.0.0.1:54321`) to production (`https://yourproject.supabase.co`).

## Schema Management & Migrations

Migrations are stored in `supabase/migrations/` and run automatically on `supabase start`.

**Current migrations**:
- `20251020000000_initial_schema.sql`: Core entities and relationships tables
- `20251021063959_add_image_url_to_entities.sql`: Add image_url column to entities
- `20251021064255_remove_description_from_entities.sql`: Remove description column (use attributes JSONB instead)
- `20251021064612_convert_image_url_to_flexible_key.sql`: Rename image_url to image_key, add get_image_url() function (superseded)
- `20251024191322_convert_image_key_to_image_url_paths.sql`: Convert image_key to image_url with path-based storage
- `20251021064735_create_collectible_images_bucket.sql`: Create images storage bucket with policies (originally collectible-images)
- `20251021065503_rename_images_bucket.sql`: Rename bucket from collectible-images to images

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
WHERE attributes @> '{"tcgplayer_id": "base1-4"}';

-- Extract JSONB values and standard columns
SELECT name, image_url, attributes->>'hp' as hp
FROM entities
WHERE type = 'card';
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

-- Relationship with attributes (e.g., order in collection)
SELECT e.*, r.attributes->>'order' as position
FROM entities e
JOIN relationships r ON r.to_id = e.id
WHERE r.from_id = 'collection-uuid'
  AND r.type = 'contains'
ORDER BY (r.attributes->>'order')::int;

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
