# Curator System Technical Reference

Complete technical specifications for the v2 curator system.

## Architecture Overview

### Design Philosophy

**Hybrid Architecture**: Python handles mechanical fetch, Claude handles intelligent import via MCP.

```
┌─────────────────┐
│  Fetch Phase    │  Python Script (fetch_data.py)
│  - API calls    │  - Handles pagination, rate limiting
│  - Parsing      │  - Outputs standardized JSON
│  - Normalization│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  fetched_data.json                      │
│  - Format version 1.0                   │
│  - Metadata (source, timestamp, filters)│
│  - Items array (normalized entities)    │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Import Phase   │  Claude via MCP Tools
│  - Deduplication│  - search_collectibles (semantic)
│  - Entity CRUD  │  - create_entity, update_entity
│  - Image linking│  - create_image
│  - Relationships│  - create_relationship
│  - Embeddings   │  - bulk_generate_embeddings
└─────────────────┘
```

**Benefits**:
- Simple fetch scripts (~200 lines vs ~500 in v1)
- Intelligent deduplication (semantic vs exact match)
- Natural language invocation
- Environment-agnostic (local vs production)

## File Formats

### fetched_data.json (v1.0)

**Location**: `.curator/curators/{Collection Name}/fetched_data.json`

**Purpose**: Standardized intermediate format between fetch and import phases.

**Schema**:
```json
{
  "format_version": "1.0",
  "metadata": {
    "curator": "Pokemon TCG",
    "source": "https://api.pokemontcg.io/v2",
    "fetched_at": "2025-11-15T14:30:00Z",
    "total_items": 100,
    "filters_applied": {
      "limit": 100,
      "expansion": "Base Set"
    }
  },
  "items": [
    {
      "name": "Base Set",
      "type": "collection",
      "year": 1999,
      "external_ids": {
        "pokemontcg_io_set": "base1"
      },
      "attributes": {
        "series": "Base",
        "total_cards": 102
      }
    },
    {
      "name": "Charizard",
      "type": "card",
      "year": 1999,
      "language": "en",
      "country": "US",
      "external_ids": {
        "pokemontcg_io": "base1-4"
      },
      "image_url": "https://images.pokemontcg.io/base1/4.png",
      "source_url": "https://pokemontcg.io/cards/base1-4",
      "parent": {
        "type": "collection",
        "external_ids": {
          "pokemontcg_io_set": "base1"
        }
      },
      "relationship": {
        "type": "contains",
        "order": 4
      },
      "attributes": {
        "hp": 120,
        "card_number": "4/102",
        "rarity": "rare"
      }
    }
  ]
}
```

**Field Specifications**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format_version` | string | Yes | Must be "1.0" |
| `metadata` | object | Yes | Fetch metadata |
| `metadata.curator` | string | Yes | Curator name |
| `metadata.source` | string | Yes | Data source URL |
| `metadata.fetched_at` | string | Yes | ISO 8601 timestamp |
| `metadata.total_items` | integer | Yes | Item count |
| `metadata.filters_applied` | object | No | Filters used |
| `items` | array | Yes | Entity array (parents + children in graph order) |
| `items[].name` | string | Yes | Display name |
| `items[].type` | string | Yes | Entity type (collection, card, comic, etc.) |
| `items[].year` | integer | No | Universal year |
| `items[].language` | string | No | ISO 639-1 code |
| `items[].country` | string | No | ISO 3166-1 alpha-2 |
| `items[].external_ids` | object | No | External system IDs (for deduplication) |
| `items[].image_url` | string | No | Image URL |
| `items[].source_url` | string | No | Source page URL |
| `items[].parent` | object | No | Parent reference (for child entities) |
| `items[].parent.type` | string | If parent | Parent entity type |
| `items[].parent.external_ids` | object | If parent | Parent external IDs (for lookup) |
| `items[].relationship` | object | No | Relationship metadata |
| `items[].relationship.type` | string | If relationship | Relationship type (e.g., "contains") |
| `items[].relationship.order` | integer | No | Sort order in relationship |
| `items[].attributes` | object | No | Custom metadata |

**Graph Structure**:

The `items` array contains BOTH parent and child entities in a graph structure:

1. **Parent entities** (collections, series, sets) come first
2. **Child entities** (cards, issues, items) reference parents via `parent` field
3. **Relationships** are explicit with `type` and optional `order`

**How it works:**
- Parent entities are identified by their `external_ids`
- Child entities reference parents using matching `external_ids`
- Claude/MCP processes in order:
  1. Check if parent exists (via external_ids lookup)
  2. Create parent if new, skip if exists
  3. Create child entity
  4. Create relationship with specified type and order

**This supports both:**
- ✅ New parent entities (first import)
- ✅ Existing parent entities (subsequent imports)

**Deduplication**:

Deduplication is handled automatically by `bulk_import_curator_batch` using `external_ids`:

1. Items with matching `external_ids` are detected as duplicates
2. `skip_duplicates=true` (default): Existing items are skipped
3. `update_existing=true`: Existing items are updated instead

**No per-item dedup configuration needed** - just include `external_ids` on items:

```json
{
  "name": "Charizard",
  "external_ids": {"pokemontcg_io": "base1-4"},
  "type": "item"
}
```

Re-running an import is always safe - duplicates are detected and handled automatically.

### config.json (v2.0)

**Location**: `.curator/curators/{Collection Name}/config.json`

**Purpose**: Curator configuration for discovery and execution.

**Schema**:
```json
{
  "curator_version": "2.0",
  "collection_name": "Pokemon TCG",
  "data_source": "https://api.pokemontcg.io/v2",
  "fetch": {
    "script": "scripts/fetch_data.py",
    "requires_api_key": true,
    "rate_limit_seconds": 0.1,
    "supports_filters": ["set", "rarity", "type"]
  },
  "deduplication": {
    "strategy": "external_id",
    "field": "pokemontcg_io",
    "fallback": "semantic",
    "semantic_threshold": 0.95
  },
  "entity_mapping": {
    "type": "card",
    "attributes": ["hp", "card_number", "rarity"]
  }
}
```

**Field Specifications**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `curator_version` | string | Yes | Must be "2.0" |
| `collection_name` | string | Yes | Display name |
| `data_source` | string | Yes | API/website URL |
| `fetch.script` | string | Yes | Fetch script path |
| `fetch.requires_api_key` | boolean | Yes | Needs API key? |
| `fetch.rate_limit_seconds` | number | No | Delay between requests |
| `fetch.supports_filters` | array | No | Available filter args |
| `deduplication.strategy` | string | Yes | "external_id" or "semantic" |
| `deduplication.field` | string | If external_id | External ID field name |
| `deduplication.fallback` | string | No | Fallback strategy |
| `deduplication.semantic_threshold` | number | No | Similarity threshold (0.95 default) |
| `entity_mapping.type` | string | Yes | Entity type |
| `entity_mapping.attributes` | array | No | Expected attribute keys |

### README.md

**Location**: `.curator/curators/{Collection Name}/README.md`

**Purpose**: Complete documentation for the curator including setup, usage, metadata structure, and troubleshooting.

**Required Sections**:
- **Overview**: Collection description, data source, organization, deduplication strategy
- **Terms of Service & Attribution**: Compliance status, requirements, attribution text
- **Setup**: API credentials, secrets configuration, test fetch, import via Claude
- **How It Works**: Fetch script behavior, import workflow via MCP
- **Metadata Structure**: Fetched data format and database entity format
- **Troubleshooting**: Common issues and solutions

See the `init-curator` skill template for the complete structure.

## Secrets Management

### Pattern

Three-file pattern for environment separation:

```
.curator/curators/{Collection Name}/
├── secrets.env               # Shared (API keys)
├── secrets.local.env         # Local (collection ID)
├── secrets.prod.env          # Production (collection ID)
├── secrets.env.example       # Template (committed)
├── secrets.local.env.example # Template (committed)
└── secrets.prod.env.example  # Template (committed)
```

**Gitignore Rule**: `.curator/.gitignore` excludes `secrets.*.env` (without .example suffix).

### secrets.env (Shared)

**Purpose**: API keys and credentials used across all environments.

**Template** (`secrets.env.example`):
```bash
# {Collection Name} Curator - Shared Configuration (All Environments)
# Copy to secrets.env and fill in your API key

# Data Source API Key
{API_KEY_VAR}=your_api_key_here

# Note: Collection IDs are environment-specific:
# - secrets.local.env (for local Supabase)
# - secrets.prod.env (for production Supabase)
```

**Example** (Pokemon TCG):
```bash
# Pokemon TCG Curator - Shared Configuration
# Copy to secrets.env and fill in your API key

# Pokemon TCG API Key (get from https://pokemontcg.io)
POKEMON_TCG_API_KEY=your_api_key_here
```

### secrets.local.env (Local Environment)

**Purpose**: Collection UUID for local Supabase instance.

**Template** (`secrets.local.env.example`):
```bash
# {Collection Name} Curator - Local Environment Configuration
# Copy to secrets.local.env and fill in your local collection ID

# Collection ID for local Supabase (http://127.0.0.1:54321)
# To get this ID:
# 1. Start local Supabase: ./bin/supabase start
# 2. Create collection: INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection') RETURNING id;
# 3. Paste the UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

### secrets.prod.env (Production Environment)

**Purpose**: Collection UUID for production Supabase instance.

**Template** (`secrets.prod.env.example`):
```bash
# {Collection Name} Curator - Production Environment Configuration
# Copy to secrets.prod.env and fill in your production collection ID

# Collection ID for production Supabase
# To get this ID:
# 1. Connect to production database
# 2. Create collection: INSERT INTO entities (name, type) VALUES ('{Collection Name}', 'collection') RETURNING id;
# 3. Paste the UUID here:
COLLECTION_ID=00000000-0000-0000-0000-000000000000
```

### Loading Secrets (Implementation)

Claude loads secrets in this order:

```bash
# 1. Shared API keys
if [ -f "$CURATOR_DIR/secrets.env" ]; then
    source "$CURATOR_DIR/secrets.env"
fi

# 2. Environment-specific collection ID
ENV_SECRETS="$CURATOR_DIR/secrets.${ENVIRONMENT}.env"
if [ -f "$ENV_SECRETS" ]; then
    source "$ENV_SECRETS"
else
    echo "❌ ERROR: Environment secrets not found: $ENV_SECRETS"
    exit 1
fi

# 3. Validate required variables
if [ -z "$COLLECTION_ID" ]; then
    echo "❌ ERROR: COLLECTION_ID not set in $ENV_SECRETS"
    exit 1
fi
```

## MCP Integration

### Available Tools

**Read Tools (5)**:
- `search_collectibles(query, entity_type, category, limit)` - Semantic search with optional category filter
- `get_entity(id)` - Get entity details
- `browse_collection(collection_id, entity_type, limit)` - List items
- `get_variants(entity_id)` - Get variants
- `get_components(entity_id)` - Get components

**Write Tools (11)**:
- `create_entity(...)` - Create new entity
- `update_entity(entity_id, ...)` - Update entity
- `delete_entity(entity_id)` - Delete entity
- `create_relationship(from_id, to_id, type, order)` - Link entities
- `delete_relationship(from_id, to_id, type)` - Unlink entities
- `create_variant(variant_of, name, ...)` - Create variant
- `update_variant(variant_id, ...)` - Update variant
- `create_component(component_of, name, ...)` - Create component
- `create_image(entity_id|variant_id|component_id, image_url, ...)` - Link image
- `generate_embedding(entity_id)` - Generate embedding
- `bulk_generate_embeddings(entity_ids[])` - Batch generate

**Curator Tools (5)**:
- `list_curators()` - List available curators
- `get_curator_config(name)` - Get curator config
- `run_curator_fetch(name, options)` - Execute fetch script
- `validate_curator_data(name, data)` - Validate fetched data
- `get_curator_stats(name)` - Get collection stats

### Import Workflow (Bulk Import)

The recommended import approach uses `bulk_import_curator_batch` for 100x+ faster imports:

```
bulk_import_curator_batch(
  collection_id: "parent-collection-uuid",
  items: [...],              // Array from fetched_data.json
  skip_duplicates: true,     // Skip items with matching external_ids (default)
  update_existing: false,    // Or update existing items
  generate_embeddings: true, // Generate text embeddings for search (default)
  localize_images: true,     // Download and store images locally (default)
  parallel_image_limit: 10   // Concurrent image downloads (default)
)
```

**What it does in a single call:**

1. **Database Transaction**: Creates all entities and relationships atomically
2. **Deduplication**: Matches existing entities by `external_ids`
3. **Text Embeddings**: Generates 384d embeddings for semantic search
4. **Image Processing**: Downloads images, generates thumbnails, uploads to storage
5. **CLIP Embeddings**: Generates 512d embeddings for reverse image search

**Return value:**
```json
{
  "success": true,
  "summary": {
    "total": 100,
    "created": 85,
    "updated": 0,
    "skipped": 15,
    "errors": 0
  },
  "created_entity_ids": ["uuid1", "uuid2", ...],
  "execution_time_ms": 45000,
  "image_processing": {
    "attempted": 85,
    "succeeded": 83,
    "failed": 2
  }
}
```

## Image Handling

**How `localize_images: true` works:**

1. **Download**: Fetches image from external URL
2. **Store Original**: Uploads to `images/originals/{entity_id}.{ext}` in Supabase storage
3. **Generate Thumbnail**: Creates 300x300 WebP thumbnail
4. **Store Thumbnail**: Uploads to `images/thumbnails/{entity_id}.webp`
5. **CLIP Embedding**: Generates 512d vector for reverse image search
6. **Link to Entity**: Creates image record with `primary_image_id` foreign key

**Why localize?**
- ✅ **Preservation**: External URLs break over time
- ✅ **Performance**: Thumbnails load faster
- ✅ **Search**: CLIP embeddings enable "find similar images"

**If you don't want to localize**: Set `localize_images: false` and images remain as external URLs (not recommended for preservation).

## Failure Handling & Recovery

### Transaction Safety

The database import runs in a **single transaction**:
- If any entity fails to create → entire batch rolls back
- Either all entities are created, or none are

### Image Processing

Image processing happens **after** the database transaction:
- If images fail, entities still exist
- Failed images logged but don't affect entity creation

### Re-running Imports

**Re-running is always safe:**

| Scenario | With `skip_duplicates: true` | With `update_existing: true` |
|----------|------------------------------|------------------------------|
| Entity exists | Skipped (no change) | Updated with new data |
| Entity is new | Created | Created |
| Image failed last time | Will retry if entity still needs image | Will retry |

**Best practice**: Keep `skip_duplicates: true` (default). If you need to update existing items, use `update_existing: true`.

### Partial Failure Example

```
First run: 100 items
  - 95 created successfully
  - 5 failed (bad data)
  - 90 images processed, 5 failed (timeouts)

Second run (same items):
  - 95 skipped (already exist)
  - 5 still fail (same bad data)
  - 0 new images (already processed)
```

**To fix the 5 failed items**: Fix the data issues in the fetch script, then re-run. The 95 good items will be skipped automatically.

## Fetch Script Template

### Template Location

`.curator/templates/fetch_data.py.template`

### Customization Points

All customization points are marked with `# CUSTOMIZE:` comments:

| Line | What to Customize | Example |
|------|-------------------|---------|
| 11 | `API_URL` constant | `"https://api.pokemontcg.io/v2"` |
| 111 | API key env var name | `POKEMON_TCG_API_KEY` |
| 31 | Pagination params | `{"page": page, "limit": 100}` |
| 46 | Response structure | `data["cards"]` vs `data["items"]` |
| 55 | Pagination check | `data.get("hasMore")` |
| 74 | Entity type | `"card"`, `"figure"`, `"game"` |
| 78 | External ID field | `"pokemontcg_io"` |
| 87-90 | Attributes mapping | `"hp": raw_item.get("hp")` |
| 103-106 | Filter arguments | `--set`, `--rarity`, `--type` |

### Required Functions

**`fetch_items(api_key, limit, **filters) -> List[dict]`**:
- Handles pagination and rate limiting
- Returns raw API responses
- Must support `limit` parameter
- Must accept `**filters` for curator-specific filters

**`normalize_item(raw_item) -> dict`**:
- Transforms API response to fetched_data.json schema
- Maps API fields to standard fields (name, type, year, etc.)
- Extracts external_id for deduplication
- Populates attributes JSONB with domain-specific metadata
- Returns dict matching fetched_data.json item schema

**`main() -> int`**:
- Parses command-line arguments (--limit, custom filters)
- Loads API key from environment
- Calls fetch_items() and normalize_item()
- Outputs fetched_data.json with format_version 1.0
- Returns 0 on success, 1 on error

### Example Implementation

See `.curator/curators/Labubu/scripts/fetch_data.py` for working example (web scraping).

For API-based example, see template comments.

## Skills

### init-curator Skill

**Location**: `.claude/skills/init-curator/SKILL.md`

**Purpose**: Interactive curator creation through Socratic questioning.

**Process**:
1. Ask questions one at a time:
   - Collection scope (what items, organization)
   - Data sources (API, website, manual)
   - Terms of Service compliance (research required)
   - Deduplication strategy
   - Attributes and metadata
2. Research ToS compliance (WebFetch ToS page)
3. Generate artifacts:
   - `README.md` (complete documentation)
   - `config.json` (v2 schema)
   - `scripts/fetch_data.py` (customized template)
   - `secrets.*.env.example` (all 3 templates)
4. Offer validation test (optional fetch --limit=5)
5. Commit curator

**Critical Requirements**:
- Must research ToS before generating scripts
- If non-compliant, STOP and suggest alternatives
- Generate complete, working fetch script (~200 lines)
- Output standardized fetched_data.json format
- Use environment variables for secrets

### run-curator Skill

**Location**: `.claude/skills/run-curator/SKILL.md`

**Purpose**: Autonomous curator execution with MCP import.

**Process**:
1. **Environment Detection** - Auto-detect local vs prod from MCP server
2. **Load Secrets** - Load secrets.env + secrets.{env}.env
3. **Fetch** - Execute fetch_data.py (autonomous debugging)
4. **Import via MCP** - For each item:
   - Deduplicate via search_collectibles
   - Create entity via create_entity
   - Link image via create_image
   - Create relationship via create_relationship
5. **Generate Embeddings** - bulk_generate_embeddings for new entities
6. **Report** - Created/Updated/Failed counts

**Critical Philosophy**:
- Errors are EXPECTED (fetch scripts fail on first run)
- Debug autonomously (read errors, fix issues, retry)
- Iterate until success (don't give up after one error)
- Use MCP tools for import (not Python scripts)
- Don't report failure without attempting fixes

**Command Variations**:
```bash
/curator:run "Collection Name"
/curator:run "Collection Name" --fetch-only
/curator:run "Collection Name" --import-only
/curator:run "Collection Name" --env=prod
/curator:run "Collection Name" --limit=50 --filter=value
```

Natural language also works: "Import latest Pokemon Base Set cards"

## Error Handling

### Fetch Errors

**Missing dependency**:
```
Error: ModuleNotFoundError: No module named 'requests'
Action: pip install requests
```

**Invalid API key**:
```
Error: 401 Unauthorized
Action: Check API_KEY in secrets.env
```

**API structure changed**:
```
Error: KeyError: 'items'
Action: Edit fetch script to match new structure
```

**Rate limiting**:
```
Error: 429 Too Many Requests
Action: Exponential backoff (1s, 2s, 4s, 8s)
```

### Import Errors

**Missing image** (non-fatal):
```
Warning: Image URL 404
Action: Log warning, continue without image
```

**Duplicate detection ambiguity**:
```
Warning: Semantic match at 0.93 (below 0.95 threshold)
Action: Create new entity, log for manual review
```

**Relationship exists** (not an error):
```
Info: Relationship already exists
Action: Log as "updated", continue
```

**Collection not found** (fatal):
```
Error: COLLECTION_ID not found in database
Action: Stop import, report error
```

## Database Schema Integration

### Entity Columns

Fetch scripts must map to these columns:

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | Auto | Generated by database |
| `type` | TEXT | Yes | "card", "figure", "game", etc. |
| `name` | TEXT | Yes | Display name |
| `year` | INT | No | Universal year attribute |
| `country` | CHAR(2) | No | ISO 3166-1 alpha-2 |
| `language` | CHAR(2) | No | ISO 639-1 code |
| `image_url` | TEXT | No | Image URL or storage path |
| `thumbnail_url` | TEXT | No | Pre-generated thumbnail path |
| `source_url` | TEXT | No | Source page URL |
| `name_embedding` | vector(384) | Auto | Generated by MCP tool |
| `external_ids` | JSONB | No | External system IDs |
| `attributes` | JSONB | No | Domain-specific metadata |

**Important**: Use dedicated columns when available (don't put year in attributes).

### External IDs Pattern

Store external system IDs in dedicated `external_ids` JSONB column:

```json
{
  "pokemontcg_io": "base1-4",
  "tcgplayer": "base1-4",
  "scryfall": "abc-123"
}
```

**Why separate column?**:
- GIN index for fast lookups
- Clear separation from domain metadata
- Supports multiple external systems

### Attributes JSONB

Use for domain-specific metadata only:

```json
{
  "hp": 120,
  "card_number": "4/102",
  "rarity": "rare",
  "description": "A legendary Fire-type Pokémon"
}
```

**Don't put here**:
- Year → use `year` column
- Language → use `language` column
- Country → use `country` column
- External IDs → use `external_ids` column
- Images → use `image_url`/`thumbnail_url` columns

## Testing

### Unit Testing (Fetch Script)

```bash
cd .curator/curators/Collection\ Name/
python3 scripts/fetch_data.py --limit=1
```

**Verify**:
1. fetched_data.json created
2. format_version is "1.0"
3. metadata section complete
4. Items have required fields (name, type)
5. External IDs present (for deduplication)

### Integration Testing (Full Workflow)

```bash
# 1. Test fetch
/curator:run "Collection Name" --fetch-only --limit=5

# 2. Inspect output
cat .curator/curators/Collection\ Name/fetched_data.json | jq '.items[0]'

# 3. Test import
/curator:run "Collection Name" --import-only

# 4. Verify in database
./scripts/semantic-search "test query" --type card
```

### Production Testing

```bash
# 1. Test locally first
/curator:run "Collection Name" --limit=10

# 2. Check results in Studio UI
# http://127.0.0.1:54323

# 3. If good, test production with small limit
/curator:run "Collection Name" --env=prod --limit=10

# 4. Full production run
/curator:run "Collection Name" --env=prod
```

## Migration from v1

### Differences

| Aspect | v1 | v2 |
|--------|----|----|
| Import | Python script (import_items.py) | Claude via MCP |
| Deduplication | External ID only | External ID + Semantic |
| Secrets | Single secrets.env | 3 files (shared + env-specific) |
| Validation | validate.py script | Claude via MCP |
| Embeddings | Python script | MCP bulk_generate_embeddings |
| Images | Python image_utils.py | MCP create_image |
| Fetch output | Array format | fetched_data.json v1.0 |
| Config | v1.0 schema | v2.0 schema |
| Fetch script | ~500 lines | ~200 lines |

### Migration Steps

For existing v1 curators:

1. **Update config.json** to v2.0 schema:
   ```json
   {
     "curator_version": "2.0",
     ...
   }
   ```

2. **Delete obsolete scripts**:
   ```bash
   rm scripts/import_items.py
   rm scripts/validate.py
   ```

3. **Update fetch script** to output fetched_data.json v1.0

4. **Create environment-specific secrets**:
   ```bash
   cp secrets.env.example secrets.local.env.example
   cp secrets.env.example secrets.prod.env.example
   # Edit templates
   ```

5. **Test with run-curator skill**:
   ```bash
   /curator:run "Collection Name" --fetch-only --limit=5
   ```

## Reference

### Command Summary

```bash
# Discovery
/curator:init "Collection Name"         # Create new curator
/curator:status "Collection Name"       # Show stats

# Execution
/curator:run "Collection Name"          # Full workflow
/curator:run "..." --fetch-only         # Fetch only
/curator:run "..." --import-only        # Import only
/curator:run "..." --env=prod           # Production
/curator:run "..." --limit=50           # Limit items
/curator:run "..." --filter=value       # Custom filter
```

### File Structure

```
.curator/curators/{Collection Name}/
├── README.md                        # Complete documentation
├── config.json                      # Curator config (v2)
├── fetched_data.json                # Fetch output (v1.0)
├── scripts/
│   └── fetch_data.py                # Fetch script
├── secrets.env                      # Shared API keys (gitignored)
├── secrets.local.env                # Local collection ID (gitignored)
├── secrets.prod.env                 # Prod collection ID (gitignored)
├── secrets.env.example              # Template (committed)
├── secrets.local.env.example        # Template (committed)
└── secrets.prod.env.example         # Template (committed)
```

### MCP Tool Summary

| Tool | Purpose | Phase |
|------|---------|-------|
| `search_collectibles` | Deduplication | Import |
| `create_entity` | Create entity | Import |
| `create_image` | Link image | Import |
| `create_relationship` | Link to collection | Import |
| `bulk_generate_embeddings` | Generate embeddings | Import |
| `run_curator_fetch` | Execute fetch script | Fetch (optional) |
| `validate_curator_data` | Validate fetched data | Validation (optional) |

### Environment Variables

| Variable | File | Purpose |
|----------|------|---------|
| `{API_KEY_VAR}` | secrets.env | API authentication |
| `COLLECTION_ID` | secrets.local.env | Local collection UUID |
| `COLLECTION_ID` | secrets.prod.env | Prod collection UUID |
| `SUPABASE_URL` | .env | Local: auto-detected |
| `SUPABASE_ANON_KEY` | .env | Local: auto-detected |
| `SUPABASE_PROD_URL` | .env | Production MCP server |
| `SUPABASE_PROD_ANON_KEY` | .env | Production MCP server |
