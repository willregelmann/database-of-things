---
name: curator-system
description: This skill should be used when the user is creating curators, running imports, debugging fetch scripts, working with fetched_data.json, or managing collection imports. Examples: "create a curator for X", "import Pokemon cards", "run curator", "fix fetch script", "curator secrets".
analyzed: 2025-12-29
source_files:
  - .claude/skills/run-curator/SKILL.md
  - .claude/skills/init-curator/SKILL.md
  - docs/curator-technical-reference.md
  - docs/curator-user-guide.md
  - mcp-server/src/tools/curator/bulk-import.ts
  - mcp-server/src/tools/curator/execution.ts
  - .curator/curators/
---

# Curator System

## What This Domain Does

The curator system provides autonomous agents for importing collectibles data from external APIs. It uses a **hybrid architecture**: Python scripts handle mechanical data fetching, while Claude handles intelligent import via MCP tools.

Curators live in `.curator/curators/{Collection Name}/` and output standardized `fetched_data.json` files that are then imported via the `bulk_import_curator_batch` MCP tool.

## Key Concepts

- **Fetch Script** (`fetch_data.py`): Python script that calls external APIs, handles pagination/rate limiting, and outputs `fetched_data.json`

- **fetched_data.json**: Standardized format (v1.0) containing metadata and items array. Both parent collections and child items in graph order.

- **Bulk Import**: The `bulk_import_curator_batch` MCP tool imports entire batches in a single transaction (100x faster than individual calls)

- **Secrets Management**: API keys in `secrets.env`, collection IDs in `secrets.local.env` / `secrets.prod.env`

- **Deduplication**: Automatic via `external_ids` - re-running imports is always safe

## How It Works

### Curator Directory Structure

```
.curator/curators/{Collection Name}/
├── README.md              # Human-readable documentation
├── config.json            # Curator configuration
├── scripts/
│   └── fetch_data.py      # Data fetching script
├── secrets.env            # API keys (shared, gitignored)
├── secrets.local.env      # Local collection ID (gitignored)
├── secrets.prod.env       # Production collection ID (gitignored)
└── fetched_data.json      # Output from fetch (gitignored)
```

### fetched_data.json Format (v1.0)

```json
{
  "format_version": "1.0",
  "metadata": {
    "curator": "Pokemon TCG",
    "source": "https://api.pokemontcg.io/v2",
    "fetched_at": "2025-11-15T14:30:00Z",
    "total_items": 100,
    "filters_applied": { "limit": 100 }
  },
  "items": [
    {
      "name": "Base Set",
      "type": "collection",
      "external_ids": { "pokemontcg_io_set": "base1" },
      "attributes": { "total_cards": 102 }
    },
    {
      "name": "Charizard",
      "type": "card",
      "external_ids": { "pokemontcg_io": "base1-4" },
      "image_url": "https://images.pokemontcg.io/base1/4.png",
      "parent": {
        "type": "collection",
        "external_ids": { "pokemontcg_io_set": "base1" }
      },
      "relationship": { "type": "contains", "order": 4 }
    }
  ]
}
```

### Bulk Import Workflow

```typescript
const result = await bulk_import_curator_batch({
  collection_id: COLLECTION_ID,
  items: fetched_data.items,
  skip_duplicates: true,        // Auto-deduplication via external_ids
  update_existing: false,       // Or true to update existing items
  generate_embeddings: true,    // Auto-generate text embeddings
  localize_images: true,        // Auto-download and process images
  parallel_image_limit: 10      // Concurrent image downloads
});

// Result:
// { success: true, summary: { created: 450, updated: 0, skipped: 50, errors: 0 } }
```

**What bulk import handles automatically:**
- Deduplication via external_ids
- Entity creation in single transaction
- Relationship creation (collection → item)
- Text embeddings (384d MiniLM)
- Image download, thumbnail, CLIP embedding
- Per-item error handling (doesn't fail entire batch)

### Secrets Management

**Three secret files per curator:**

1. `secrets.env` - Shared API keys:
```bash
API_KEY=your_api_key_here
```

2. `secrets.local.env` - Local environment:
```bash
COLLECTION_ID=uuid-of-local-collection
```

3. `secrets.prod.env` - Production environment:
```bash
COLLECTION_ID=uuid-of-prod-collection
```

**Loading order:**
```bash
source "$CURATOR_DIR/secrets.env"           # API keys
source "$CURATOR_DIR/secrets.${ENV}.env"    # Collection ID
```

## Important Files

- `.claude/skills/run-curator/SKILL.md`: Complete autonomous run workflow
- `.claude/skills/init-curator/SKILL.md`: Interactive curator creation
- `docs/curator-technical-reference.md`: Format specifications
- `mcp-server/src/tools/curator/bulk-import.ts`: Bulk import implementation
- `.curator/curators/`: Existing curator implementations (Pokemon TCG, LEGO Sets, etc.)

## Working With This Domain

### Creating a New Curator

Use `/curator:init "Collection Name"` or the `init-curator` skill. Claude will:
1. Ask Socratic questions about data source, ToS, metadata
2. Generate `fetch_data.py` script
3. Create config files and secrets templates
4. Test the fetch with `--limit=5`

### Running a Curator

Use `/curator:run "Collection Name"` or natural language. The workflow:

1. **Load configuration**: Read config.json and secrets
2. **Fetch data**: Run `fetch_data.py` via MCP or Bash
3. **Import via MCP**: Call `bulk_import_curator_batch` with all items
4. **Report results**: Created/updated/skipped/failed counts

### Debugging Fetch Scripts

Common issues and fixes:

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: requests` | `pip install requests` |
| `401 Unauthorized` | Check API key in secrets.env |
| `JSONDecodeError` | API response format changed, update parsing |
| `KeyError: 'items'` | API structure changed, update field access |
| `ConnectionError` | Check API URL, add retry logic |

**Key principle**: Errors are expected on first run. Debug autonomously, fix issues, retry.

### Graph Import (Parent + Child)

When fetched data contains hierarchies:

1. **Parents come first** in items array (no `parent` field)
2. **Children reference parents** via `parent.external_ids`
3. **Import processes in order**: creates parents, then children with relationships

```json
{
  "items": [
    { "name": "Series", "type": "collection", "external_ids": {"series_id": "1"} },
    {
      "name": "Issue #1",
      "type": "comic",
      "parent": { "type": "collection", "external_ids": {"series_id": "1"} },
      "relationship": { "type": "contains", "order": 1 }
    }
  ]
}
```

### Environment Detection

The curator system detects environment from:
1. Explicit flag: `--env=prod` or `--env=local`
2. Active MCP server: `database-of-things-local` → local, `database-of-things-prod` → prod
3. Default: local

### Common Mistakes to Avoid

- **Don't skip secrets files**: Both `secrets.env` and `secrets.{env}.env` are required
- **Don't forget external_ids**: Items without external_ids can't be deduplicated
- **Don't hardcode collection IDs**: Use environment-specific secrets
- **Don't ignore errors**: Debug and fix, don't just report failure
- **Don't use individual MCP calls for bulk import**: Use `bulk_import_curator_batch` (100x faster)

### Available Curators

Current curators in `.curator/curators/`:
- Pokemon TCG
- Pokemon TCG Shadowless Variants
- Power Rangers Toys
- LEGO Sets
- American Comics
- NTSC Video Games

### Commands

```bash
/curator:init "Collection Name"    # Create new curator
/curator:run "Collection Name"     # Run full workflow
/curator:run "Name" --fetch-only   # Fetch without import
/curator:run "Name" --import-only  # Import existing fetched_data.json
/curator:run "Name" --env=prod     # Use production environment
/curator:status "Name"             # Show collection stats
```
