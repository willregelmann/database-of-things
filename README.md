# Database of Things

A minimal, pure graph database for managing collectibles using PostgreSQL via Supabase.

## Overview

This project provides a flexible collectibles management system built on a graph-based architecture using PostgreSQL (entities + relationships).

**Core Philosophy**: Everything is an entity (collections, items, variants, etc.), connected by typed relationships. No fixed schema beyond the essentials.

## Quick Start

### Database Setup

```bash
# Start Supabase stack
./bin/supabase start

# Apply migrations
./scripts/safe-migrate push

# View Studio UI
open http://127.0.0.1:54323
```

## Features

### Graph Database

- **Pure Graph Model**: Three tables (entities, relationships, variants) handle everything
- **Flexible Schema**: JSONB attributes for heterogeneous data
- **GraphQL API**: Auto-generated from database schema
- **Semantic Search**: Vector embeddings with pgvector for intelligent search
- **Image Storage**: Supabase Storage with pre-generated thumbnails
- **Optimized Indexes**: Composite, covering, BRIN, GIN, HNSW indexes for fast queries

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Supabase Stack                            │
│  • PostgreSQL (graph database)                               │
│  • GraphQL API (auto-generated)                              │
│  • Storage (images + thumbnails)                             │
│  • Auth, Realtime, REST APIs                                 │
└──────────────────────────────────────────────────────────────┘
```

## Project Structure

```
.
├── scripts/                        # Helper scripts
│   ├── safe-migrate                # Safe migration wrapper
│   ├── db-backup                   # Manual backup
│   ├── db-restore                  # Restore from backup
│   ├── seed-sample-data.py         # Seed test data
│   ├── generate-embeddings.py     # Generate semantic search embeddings
│   ├── semantic-search             # CLI semantic search utility
│   ├── verify-schema-sync.sh       # Verify local/prod sync
│   └── thumbnails/                 # Thumbnail generation
├── supabase/                       # Supabase configuration
│   ├── config.toml                 # Supabase config
│   └── migrations/                 # Database migrations
├── .curator/                       # Curator system
│   ├── curators/                   # Collection-specific curators
│   └── lib/                        # Shared utilities
├── CLAUDE.md                       # Project guidelines for AI
├── MIGRATION_STATUS.md             # Migration tracking status
└── THUMBNAIL_QUICKSTART.md         # Image optimization guide
```

## Database Schema

### Entities Table

Everything is an entity:

```sql
CREATE TABLE entities (
  id UUID PRIMARY KEY,
  type TEXT NOT NULL,              -- "collection", "card", "figure", etc.
  name TEXT NOT NULL,
  year INT,
  country CHAR(2),                 -- ISO country code
  language CHAR(2),                -- ISO language code
  image_url TEXT,                  -- Original image path
  thumbnail_url TEXT,              -- Pre-generated thumbnail
  attributes JSONB,                -- Flexible JSONB data
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

### Variants Table

Alternative versions of entities (e.g., 1st Edition, Shadowless):

```sql
CREATE TABLE variants (
  id UUID PRIMARY KEY,
  variant_of UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  name TEXT NOT NULL,              -- Variant name
  image_url TEXT,                  -- Original image path
  thumbnail_url TEXT,              -- Pre-generated thumbnail
  attributes JSONB,                -- Variant-specific metadata
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

### Relationships Table

Typed connections between entities:

```sql
CREATE TABLE relationships (
  id UUID PRIMARY KEY,
  from_id UUID REFERENCES entities(id),
  to_id UUID REFERENCES entities(id),
  type TEXT NOT NULL,              -- "contains", "part_of"
  "order" INT,                     -- Sort order for collections
  created_at TIMESTAMPTZ
);
```

### Common Patterns

**Collection Hierarchy**:
```
Franchise → Game → Expansion → Card
(all "contains" relationships)
```

**Variants**:
```
Base Entity ← Variant
(variants table, variant_of foreign key)
```

Note: Legacy variants may exist as entities with `variant_of` relationships.

**Components**:
```
Whole Item ← Component
(part_of relationship)
```

## Key Workflows

### 1. Manual Import

```bash
# Direct SQL or GraphQL
# See CLAUDE.md for query examples
```

### 2. Image Management

```bash
# Generate thumbnails for existing images
cd scripts/thumbnails
npm install
npm run backfill

# See THUMBNAIL_QUICKSTART.md for details
```

## Documentation

- **`CLAUDE.md`**: Comprehensive project guide (architecture, commands, patterns)
- **`MIGRATION_STATUS.md`**: Migration tracking status (current: 33/33 synced ✅)
- **`MIGRATION_SYNC_PLAN.md`**: Migration synchronization guide
- **`THUMBNAIL_QUICKSTART.md`**: Image optimization guide
- **`BACKUP_SYSTEM.md`**: Database backup documentation
- **`scripts/README.md`**: Utility scripts documentation

## Development Commands

### Supabase

```bash
# Start services
./bin/supabase start

# Check status
./bin/supabase status

# View logs
./bin/supabase logs

# Stop services
./bin/supabase stop
```

### Database

```bash
# Create migration
./bin/supabase migration new name

# Apply migrations (with automatic backup)
./scripts/safe-migrate push

# Reset database (with confirmation)
./scripts/safe-migrate reset

# Seed local database with sample data
python3 scripts/seed-sample-data.py

# Generate embeddings for semantic search
python3 scripts/generate-embeddings.py

# Test semantic search
export SUPABASE_URL="http://127.0.0.1:54321"
export SUPABASE_ANON_KEY="sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH"
./scripts/semantic-search "pokemon" --type card

# Manual backup
./scripts/db-backup

# Restore backup
./scripts/db-restore backups/backup_*.sql
```

## Cost Savings

### Image Thumbnails

Pre-generating 300x300 WebP thumbnails achieves:

- **97.6% size reduction** (measured on production images)
- **$60,300/year saved** at 100K images (vs Supabase Pro image transforms)
- **Instant loading** (no on-demand processing)

## Deployment

### Local Development

```bash
# Supabase
./bin/supabase start
```

### Production

**Supabase**: Deploy to [Supabase Cloud](https://supabase.com) or self-host

## Contributing

This is a personal project, but contributions are welcome:

1. Follow existing architecture
2. Test thoroughly
3. Update documentation
4. File issues for bugs

## License

MIT License - see LICENSE file

## Support

- File issues in the repository
- Check `CLAUDE.md` for detailed documentation
