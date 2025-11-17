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
| `items[].dedup_hint` | object | No | **RARELY USED** - Override curator-level dedup strategy |

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

**Deduplication Strategy**:

⚠️ **IMPORTANT**: Deduplication strategy is defined at the **curator level** in `config.json`, NOT on individual items.

**DO NOT include `dedup_hint` on items** unless that specific item needs a DIFFERENT strategy than the curator default. This is rare.

**Curator-level (config.json)** - Use this:
```json
{
  "deduplication": {
    "strategy": "external_id",
    "field": "pokemontcg_io",
    "fallback": "semantic",
    "semantic_threshold": 0.95
  }
}
```

**Per-item override** - Only use if this specific item is different:
```json
{
  "name": "Special Card",
  "external_id": "123",
  "dedup_hint": {
    "strategy": "semantic",
    "semantic_threshold": 0.90
  }
}
```

- `strategy`: "external_id" or "semantic"
- `field`: External ID field name (for external_ids JSONB column)
- `fallback`: "semantic" to fall back if external ID not found

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
- `search_collectibles(query, entity_type, limit)` - Semantic search
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

### Import Workflow (MCP Implementation)

**Pseudocode**:
```python
# Load fetched data
with open('fetched_data.json') as f:
    data = json.load(f)

stats = {created: 0, updated: 0, failed: 0}
created_entity_ids = []

for item in data['items']:
    try:
        # Step 1: Deduplication
        existing = None

        # Strategy 1: External ID
        if item.get('external_id') and item['dedup_hint']['strategy'] == 'external_id':
            results = search_collectibles(
                query=item['external_id'],
                entity_type=item['type'],
                limit=1
            )
            # Verify exact match on external_ids field
            if results and results[0].external_ids.get(item['dedup_hint']['field']) == item['external_id']:
                existing = results[0].id

        # Strategy 2: Semantic fallback
        if not existing and item['dedup_hint'].get('fallback') == 'semantic':
            results = search_collectibles(
                query=item['name'],
                entity_type=item['type'],
                limit=3
            )
            # High confidence threshold
            if results and results[0].similarity > 0.95:
                existing = results[0].id

        # Step 2: Create or update
        if existing:
            # Entity exists - create relationship
            create_relationship(
                from_id=COLLECTION_ID,
                to_id=existing,
                type="contains"
            )
            stats['updated'] += 1
        else:
            # Create new entity
            entity_id = create_entity(
                name=item['name'],
                type=item['type'],
                year=item.get('year'),
                language=item.get('language'),
                country=item.get('country'),
                source_url=item.get('source_url'),
                external_ids={item['dedup_hint']['field']: item['external_id']} if item.get('external_id') else {},
                attributes=item.get('attributes', {})
            )

            # Link image
            if item.get('image_url'):
                create_image(
                    entity_id=entity_id,
                    image_url=item['image_url'],
                    is_primary=True,
                    source_url=item.get('source_url')
                )

            # Create relationship
            create_relationship(
                from_id=COLLECTION_ID,
                to_id=entity_id,
                type="contains"
            )

            stats['created'] += 1
            created_entity_ids.append(entity_id)

    except Exception as e:
        log_error(f"Failed to import {item['name']}: {e}")
        stats['failed'] += 1
        continue

# Step 3: Generate embeddings
if created_entity_ids:
    bulk_generate_embeddings(created_entity_ids)
```

## Deduplication Strategies

### External ID Strategy

**When to use**: Source provides stable unique IDs.

**Configuration**:
```json
{
  "dedup_hint": {
    "strategy": "external_id",
    "field": "pokemontcg_io",
    "fallback": "semantic"
  }
}
```

**Matching algorithm**:
1. Search by external ID (exact match in query)
2. Verify match has same external_ids field value
3. If found: Link to existing entity
4. If not found: Fall back to semantic (if configured)

**Example**:
```json
{
  "external_id": "base1-4",
  "dedup_hint": {"strategy": "external_id", "field": "pokemontcg_io"}
}
```

Searches for entities where `external_ids->>'pokemontcg_io' = 'base1-4'`.

### Semantic Strategy

**When to use**: No stable IDs, or handling noisy data.

**Configuration**:
```json
{
  "dedup_hint": {
    "strategy": "semantic",
    "fallback": null
  }
}
```

**Matching algorithm**:
1. Search by entity name (vector similarity)
2. Check top 3 results
3. If similarity > 0.95 (configurable): Match found
4. If no high-confidence match: Create new entity

**Why 0.95 threshold?**:
- 0.99+: Too strict, misses valid matches
- 0.90-0.94: Too loose, false positives
- 0.95: Sweet spot for high confidence

**Example**:
```
Query: "Charizard"
Results:
  1. "Charizard" (similarity: 0.98) ← Match!
  2. "Charizard EX" (similarity: 0.93) ← No match (different card)
  3. "Charmeleon" (similarity: 0.85) ← No match
```

### Hybrid Strategy

**Recommended**: Use external ID with semantic fallback.

**Configuration**:
```json
{
  "dedup_hint": {
    "strategy": "external_id",
    "field": "pokemontcg_io",
    "fallback": "semantic"
  }
}
```

**Flow**:
1. Try external ID first (fast, exact)
2. If not found, try semantic (handles missing IDs)
3. If still no match, create new entity

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
5. dedup_hint structure correct
6. External IDs present (if applicable)

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
