# Database of Things

A minimal, pure graph database for managing collectibles using PostgreSQL via Supabase, with autonomous curator agents for automated imports.

## Overview

This project provides a flexible collectibles management system with two key components:

1. **Graph Database**: Pure graph-based architecture using PostgreSQL (entities + relationships)
2. **Curator Agents**: Autonomous AI agents that discover, scrape, and import collectibles

**Core Philosophy**: Everything is an entity (collections, items, variants, etc.), connected by typed relationships. No fixed schema beyond the essentials. Curators autonomously learn the best strategies for managing each collection.

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

### Curator Setup

```bash
cd curators

# Install dependencies
pip install -e .

# Initialize environment
curator init

# Start services
docker-compose up -d

# Create your first curator
curator setup

# Run it
curator run your-curator-id
```

See `curators/QUICKSTART.md` for detailed setup.

## Features

### Graph Database

- **Pure Graph Model**: Two tables (entities, relationships) handle everything
- **Flexible Schema**: JSONB attributes for heterogeneous data
- **GraphQL API**: Auto-generated from database schema
- **Image Storage**: Supabase Storage with pre-generated thumbnails
- **Optimized Indexes**: Composite, covering, BRIN, GIN indexes for fast queries

### Curator Agents

- **🤖 Autonomous Operation**: AI agents that learn over time
- **🧠 Long-Term Memory**: Tiered importance strategy with Mem0
- **💰 Token Budget Management**: Automatic cost control
- **⚡ Rate Limiting**: Built-in throttling with exponential backoff
- **📊 Real-Time Progress**: Structured event system for monitoring
- **🎨 Collection-Agnostic**: Reusable utilities for any collectible type

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Curator Agents                          │
│  (DeepAgents + LangGraph + Mem0 for autonomous imports)      │
└────────────────┬─────────────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────────────┐
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
├── curators/                   # Autonomous curator agents
│   ├── cli/                   # CLI commands
│   ├── core/                  # Core functionality
│   ├── utilities/             # Collection-agnostic utilities
│   ├── workflows/             # LangGraph workflows
│   ├── docker-compose.yml     # Curator services
│   ├── README.md              # Curator documentation
│   └── QUICKSTART.md          # 5-minute setup guide
├── scripts/                   # Helper scripts
│   ├── safe-migrate           # Safe migration wrapper
│   ├── db-backup              # Manual backup
│   ├── db-restore             # Restore from backup
│   └── thumbnails/            # Thumbnail generation
├── supabase/                  # Supabase configuration
│   ├── config.toml            # Supabase config
│   └── migrations/            # Database migrations
├── CLAUDE.md                  # Project guidelines for AI
├── CURATOR_ARCHITECTURE_FINAL.md  # Curator design docs
└── THUMBNAIL_QUICKSTART.md    # Thumbnail system guide
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

### Relationships Table

Typed connections between entities:

```sql
CREATE TABLE relationships (
  id UUID PRIMARY KEY,
  from_id UUID REFERENCES entities(id),
  to_id UUID REFERENCES entities(id),
  type TEXT NOT NULL,              -- "contains", "variant_of", "part_of"
  "order" INT,                     -- Sort order for collections
  attributes JSONB,                -- Relationship-specific data
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
Base Item ← Variant Item
(variant_of relationship)
```

**Components**:
```
Whole Item ← Component
(part_of relationship)
```

## Key Workflows

### 1. Manual Import (Traditional)

```bash
# Direct SQL or GraphQL
# See CLAUDE.md for query examples
```

### 2. Automated Import (Curators)

```bash
# Create curator for your collection
cd curators
curator setup

# Run it (learns over time)
curator run pokemon-tcg

# Monitor progress
curator status pokemon-tcg
curator budget pokemon-tcg
```

### 3. Image Management

```bash
# Generate thumbnails for existing images
cd scripts/thumbnails
npm install
npm run backfill

# See THUMBNAIL_QUICKSTART.md for details
```

## Documentation

- **`CLAUDE.md`**: Comprehensive project guide
- **`curators/README.md`**: Curator agent documentation
- **`curators/QUICKSTART.md`**: 5-minute curator setup
- **`CURATOR_ARCHITECTURE_FINAL.md`**: Curator design and implementation
- **`THUMBNAIL_QUICKSTART.md`**: Image optimization guide
- **`BACKUP_SYSTEM.md`**: Database backup documentation

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

# Manual backup
./scripts/db-backup

# Restore backup
./scripts/db-restore backups/backup_*.sql
```

### Curators

```bash
cd curators

# Setup new curator
curator setup

# List curators
curator list

# Run curator
curator run <id>

# Check status
curator status <id>

# View token budget
curator budget <id>
```

## Curator Examples

### Pokémon TCG

```bash
curator setup
# ID: pokemon-tcg
# Type: cards
# API: pokemontcg.io

curator run pokemon-tcg
```

### Power Rangers Toys

```bash
curator setup
# ID: power-rangers
# Type: toys
# Source: GRNRngr.com scraping

curator run power-rangers
```

### Custom Collection

```bash
curator setup
# ID: your-collection
# Provide custom prompt and data sources

curator run your-collection --instructions "Import only items from 2023"
```

## Cost Savings

### Image Thumbnails

Pre-generating 300x300 WebP thumbnails achieves:

- **97.6% size reduction** (measured on production images)
- **$60,300/year saved** at 100K images (vs Supabase Pro image transforms)
- **Instant loading** (no on-demand processing)

### Token Budget Management

Curators automatically enforce daily token limits:

- Default: 1,000,000 tokens/day
- 10% buffer reserved for critical operations
- Real-time tracking via Redis
- Prevents runaway costs

## Deployment

### Local Development

```bash
# Supabase
./bin/supabase start

# Curators
cd curators && docker-compose up -d
```

### Production

**Supabase**: Deploy to [Supabase Cloud](https://supabase.com) or self-host

**Curators**: Self-hosted via Docker Compose (included)

See `curators/README.md` for scaling and deployment details.

## Contributing

This is a personal project, but contributions are welcome:

1. Follow existing architecture
2. Test thoroughly
3. Update documentation
4. File issues for bugs

## Roadmap

### Phase 1: Foundation ✅ (Weeks 1-2)

- [x] Graph database schema
- [x] Image optimization system
- [x] Curator framework
- [x] Collection-agnostic utilities
- [x] CLI and setup wizard

### Phase 2: Reference Curator (Weeks 3-4)

- [ ] Pokémon TCG reference implementation
- [ ] End-to-end workflow testing
- [ ] Memory strategy refinement
- [ ] Best practices documentation

### Phase 3: Multiple Curators (Weeks 5-6)

- [ ] Scheduling support
- [ ] Curator coordination
- [ ] Manual approval workflow
- [ ] Dashboard (optional)

### Phase 4: Optimization (Weeks 7-8)

- [ ] Performance tuning
- [ ] Cost reduction
- [ ] Production deployment guide
- [ ] Monitoring and observability

## License

MIT License - see LICENSE file

## Support

- File issues in the repository
- Check `CLAUDE.md` for detailed documentation
- See `curators/README.md` for curator-specific help
