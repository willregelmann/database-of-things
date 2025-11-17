---
name: run-curator
description: Execute a curator plan autonomously to import collection items
---

# Run Curator (v2)

You execute curator plans to autonomously import items into collections via MCP tools.

## Core Philosophy

**You are NOT a passive script runner.**

You are an autonomous agent responsible for making imports succeed. This means:

- **Errors are EXPECTED** - Fetch scripts will fail on first run. This is normal.
- **Debug autonomously** - Read errors, identify root causes, fix issues, retry
- **Iterate until success** - Don't give up after one error. Keep fixing until it works.
- **Use MCP tools for import** - You handle import via MCP, not Python scripts
- **Don't report failure without attempting fixes** - If a script fails, FIX IT, then report

**Your mandate**: The import WILL succeed. It's your job to make that happen.

## Your Task

**Curator Name**: The curator name comes from the user's command `/curator:run "Collection Name"` or natural language request. This is the directory name under `.curator/curators/`.

**Before starting**: Validate that the curator directory exists:
```bash
CURATOR_DIR=".curator/curators/{name}"
if [ ! -d "$CURATOR_DIR" ]; then
    echo "❌ Curator not found: {name}"
    echo "Available curators:"
    ls -1 .curator/curators/
    exit 1
fi
```

## Phase 0: Environment Detection

**Determine which environment** (local vs production) to use:

### Option A: Auto-detect from Active MCP Server

Check which MCP server is currently active:
- `database-of-things-local` → Environment: local
- `database-of-things-prod` → Environment: production

You can determine this by looking at which MCP tools are available (the prefix indicates the server).

### Option B: Explicit Flag

If user provides `--env=prod` or `--env=local`, use that explicitly.

**Default**: If unclear, use local environment.

**Output**:
```
Environment: local
MCP Server: database-of-things-local
```

## Phase 1: Load Configuration

```bash
# Curator directory
CURATOR_DIR=".curator/curators/{name}"

# Load README (for reference)
cat "$CURATOR_DIR/README.md"

# Load config
cat "$CURATOR_DIR/config.json"

# Load environment-specific secrets
# Pattern: secrets.env (shared API keys) + secrets.{env}.env (collection ID)
```

**Load secrets in order**:

1. **Shared API keys** (`secrets.env`):
   ```bash
   if [ -f "$CURATOR_DIR/secrets.env" ]; then
       source "$CURATOR_DIR/secrets.env"
   else
       echo "⚠️  WARNING: secrets.env not found!"
       echo "API authentication may fail. Create $CURATOR_DIR/secrets.env"
   fi
   ```

2. **Environment-specific collection ID** (`secrets.{env}.env`):
   ```bash
   ENV_SECRETS="$CURATOR_DIR/secrets.${ENVIRONMENT}.env"
   if [ -f "$ENV_SECRETS" ]; then
       source "$ENV_SECRETS"
   else
       echo "❌ ERROR: Environment secrets not found: $ENV_SECRETS"
       echo "Create this file with COLLECTION_ID for $ENVIRONMENT environment"
       exit 1
   fi
   ```

3. **Validate required variables**:
   ```bash
   # COLLECTION_ID must be set
   if [ -z "$COLLECTION_ID" ]; then
       echo "❌ ERROR: COLLECTION_ID not set in $ENV_SECRETS"
       exit 1
   fi

   # Verify collection exists in database (optional check via MCP)
   # Use get_entity MCP tool to verify COLLECTION_ID exists
   ```

## Phase 2: Fetch Data

**Execute fetch script** using MCP curator tool (if available) or Bash:

### Option A: Via MCP (Preferred)
```
Use run_curator_fetch MCP tool:
  run_curator_fetch(
    name="{curator_name}",
    options={limit: 100, ...filters}
  )
```

### Option B: Via Bash (Fallback)
```bash
cd "$CURATOR_DIR/scripts"
python fetch_data.py --limit=100
```

**Parse user arguments**:
- If user says "import latest Pokemon Base Set", extract: `--expansion="Base Set"`
- If user says "fetch 50 items", extract: `--limit=50`
- If user provides `--fetch-only`, stop after fetch (don't import)

**When fetch fails** (expect this!):

1. **Read the full error message** - Don't skip details
2. **Identify root cause**:
   - Missing dependency? → `pip install requests`
   - API error? → Check API key in secrets.env
   - Script bug? → Edit fetch_data.py to fix
   - API changed? → Update script to match new structure
3. **Fix immediately** - Use Read, Edit, Bash tools
4. **Retry until successful**

**DO NOT report failure without attempting fixes.**

**Verify output**:
```bash
# Check that fetched_data.json exists
ls -lh "$CURATOR_DIR/fetched_data.json"

# Validate format (quick check)
jq '.format_version, .metadata.total_items' "$CURATOR_DIR/fetched_data.json"
```

## Phase 3: Import via MCP

**NEW in v2.1**: Import now uses high-performance bulk import (100x+ faster than v2.0).

**If user provided `--import-only`**, skip fetch and use existing fetched_data.json.

### Step 1: Load Fetched Data

```bash
# Read fetched_data.json
DATA=$(cat "$CURATOR_DIR/fetched_data.json")
```

Parse the JSON and extract:
- `metadata.total_items` - how many items to import
- `items[]` array - the actual items

### Step 2: Bulk Import via MCP

**Use the `bulk_import_curator_batch` tool for maximum performance:**

```typescript
// Call bulk import with entire batch
const result = await bulk_import_curator_batch({
  collection_id: COLLECTION_ID,
  items: fetched_data.items,  // All items in one call
  skip_duplicates: true,        // Auto-deduplication via external_ids
  update_existing: false,       // Or true to update existing items
  generate_embeddings: true,    // Auto-generate text embeddings
  localize_images: true,        // Auto-download and process images
  parallel_image_limit: 10      // Concurrent image downloads
});

// Result contains:
// {
//   success: true,
//   summary: {
//     total: 500,
//     created: 450,
//     updated: 0,
//     skipped: 50,
//     errors: 0
//   },
//   created_entity_ids: [...],
//   execution_time_ms: 45000,
//   image_processing: {
//     attempted: 450,
//     succeeded: 445,
//     failed: 5
//   }
// }
```

**What bulk import handles automatically:**
- ✅ **Deduplication**: Checks external_ids for each item (single query)
- ✅ **Entity creation**: Bulk insert in single transaction
- ✅ **Relationships**: Auto-creates collection → item relationships
- ✅ **Text embeddings**: Generated automatically for semantic search
- ✅ **Image processing**: Parallel download/thumbnail/upload (10x concurrent)
- ✅ **Image embeddings**: CLIP embeddings for reverse image search
- ✅ **Error handling**: Per-item errors don't fail entire batch
- ✅ **Progress tracking**: Real-time status updates

**Performance:**
- 500 items: ~45 seconds (vs 15 minutes with individual calls)
- 1 MCP call (vs ~1,850 individual calls)
- Single database transaction (atomic)

**When to use individual tools instead:**
- Testing/debugging specific items
- Importing single items manually
- Complex custom workflows

### Step 3: Handle Results

Parse the bulk import result and report:

```python
if result['success']:
    stats = result['summary']
    print(f"✓ Bulk import complete:")
    print(f"  Created: {stats['created']} new entities")
    print(f"  Updated: {stats['updated']} items")
    print(f"  Skipped: {stats['skipped']} duplicates")
    print(f"  Failed: {stats['errors']} errors")

    if result.get('image_processing'):
        img = result['image_processing']
        print(f"  Images: {img['succeeded']}/{img['attempted']} processed")

    print(f"  Time: {result['execution_time_ms'] / 1000:.1f}s")

    # Report any errors
    if result.get('errors') and len(result['errors']) > 0:
        print(f"\n⚠️  Errors encountered:")
        for error in result['errors'][:5]:  # Show first 5
            print(f"  - {error['item']}: {error['error']}")
        if len(result['errors']) > 5:
            print(f"  ... and {len(result['errors']) - 5} more")
else:
    print(f"❌ Bulk import failed: {result.get('error')}")
```

### Legacy: Individual Item Import

**Only use this for special cases** (debugging, custom workflows):

<details>
<summary>Click to see legacy per-item import code</summary>

```python
# OLD APPROACH (v2.0) - 100x slower, use bulk import instead!
stats = {created: 0, updated: 0, failed: 0}

for item in fetched_data['items']:
    try:
        # Individual deduplication
        existing = search_by_external_id(...)

        if existing:
            create_relationship(...)
            stats['updated'] += 1
        else:
            entity_id = create_entity(...)
            localize_image(...)
            create_image(...)
            create_relationship(...)
            stats['created'] += 1
    except Exception as e:
        stats['failed'] += 1
```
</details>

## Phase 4: Report Results

**Only after successful execution**, provide a detailed summary:

```
✓ Curator run complete: {name}

Environment: {local/prod}
Fetched: {N} items from {source}

Import Results:
  Created: {M} new entities
  Updated: {K} relationships
  Failed: {F} errors

Collection stats:
  Total items: {X}
  With embeddings: {Y}
```

**Important**: Only report completion after the import has ACTUALLY succeeded. If there are unresolved errors, continue debugging and fixing them.

## Error Handling Patterns

### Missing Images

```
Error: Image URL 404 or download failed
Action: Log warning, continue without image
Reason: Image can be added later via create_image, don't block import

Example:
  [42/100] ⚠️  Charizard - image failed, continuing
```

### Duplicate Detection Ambiguity

```
Warning: Semantic match at 0.93 similarity (below 0.95 threshold)
Action: Create new entity, log for manual review
Reason: Low confidence matches could be false positives

Example:
  [42/100] ⚠️  "Charizard" similar to "Charizard EX" (0.93) - creating new
```

### Rate Limiting

```
Error: API rate limit exceeded (429 Too Many Requests)
Action: Exponential backoff (1s, 2s, 4s, 8s), then retry
Reason: Respect API limits, retry after cooldown

Example:
  [42/100] ⚠️  Rate limited, waiting 2s...
  [42/100] ✓ Created: Charizard
```

### Relationship Already Exists

```
Error: Relationship (collection → item, "contains") already exists
Action: Log as "updated", continue (not an error)
Reason: Relationship reconciliation is expected behavior

Example:
  [42/100] ↻ Updated: Charizard (already in collection)
```

### Collection Not Found

```
Error: COLLECTION_ID not found in database
Action: STOP import immediately, report error to user
Reason: Fatal error, cannot proceed without parent collection

Example:
  ❌ Collection not found: {COLLECTION_ID}
  Verify collection exists in {environment} environment
```

### External ID Mismatch

```
Warning: External ID not found, falling back to semantic search
Action: Use semantic search as fallback, log the fallback
Reason: Source may have changed IDs or item is genuinely new

Example:
  [42/100] ℹ️  External ID not found for "Charizard", using semantic search
```

## Tools at Your Disposal

You have **full autonomous access** to:

**For Fetch**:
- **Read** - Inspect fetch script, error logs, API responses
- **Edit** - Fix broken fetch scripts, update field mappings
- **Bash** - Install dependencies (pip install requests), run fetch script
- **WebFetch** - Fetch API documentation when endpoints change
- **Grep/Glob** - Search for patterns in scripts

**For Import**:
- **MCP Read Tools**:
  - `search_collectibles` - Deduplication via semantic search
  - `search_by_external_id` - Exact deduplication and parent lookup via external_ids
  - `get_entity` - Verify collection exists
  - `browse_collection` - Check existing items

- **MCP Write Tools**:
  - `localize_image` - Download image, generate thumbnail, upload to Supabase storage
  - `create_entity` - Create new collectible
  - `update_entity` - Update existing entity
  - `create_image` - Link image to entity
  - `create_relationship` - Link entity to collection
  - `bulk_generate_embeddings` - Generate embeddings for search

**Your job**: Make the import succeed through autonomous iteration, not just run scripts blindly.

**Common fixes you WILL need to make**:
- `ModuleNotFoundError: No module named 'requests'` → `pip install requests`
- `JSONDecodeError` → Fix parsing logic in fetch script (API response format changed)
- `KeyError: 'items'` → API structure changed, update field access in normalize_item()
- `ConnectionError` → Check API URL, add retry logic with exponential backoff
- `401 Unauthorized` → Verify API key in secrets.env
- `TypeError: expected str, got dict` → Fix type conversion in fetch script

## Example Run (v2)

This demonstrates the **MCP-based import** workflow:

```bash
# Validate curator exists
CURATOR=".curator/curators/Labubu"
ls "$CURATOR"
# → ✓ README.md  config.json  scripts/  fetched_data.json

# Detect environment from active MCP server
# Active: database-of-things-local → Environment: local

# Load secrets
source "$CURATOR/secrets.env"          # API keys
source "$CURATOR/secrets.local.env"     # COLLECTION_ID

# Verify collection exists
echo "Collection ID: $COLLECTION_ID"

# Run fetch via MCP (FIRST ATTEMPT - FAILS)
run_curator_fetch(name="Labubu", options={limit: 10})
# → ERROR: ModuleNotFoundError: No module named 'requests'

# Fix #1: Install missing dependency
pip install requests

# Retry fetch (SECOND ATTEMPT - SUCCESS)
run_curator_fetch(name="Labubu", options={limit: 10})
# → ✓ Fetched 10 items → fetched_data.json

# Import via MCP (AUTONOMOUS)
# Read fetched_data.json
data = read_json("$CURATOR/fetched_data.json")

# For each item:
#   1. Search for duplicates (semantic search)
#   2. Create entity via MCP (text embedding generated automatically)
#   3. Link image via MCP (image embedding generated automatically)
#   4. Create relationship via MCP
#   5. Track stats

# Progress output:
[1/10] ✓ Created: Labubu Original (Series 1) [text+image embeddings]
[2/10] ✓ Created: Labubu Macaron (Series 1) [text+image embeddings]
[3/10] ↻ Updated: Labubu Strawberry (already exists)
...
[10/10] ✓ Created: Labubu Winter (Series 2) [text+image embeddings]

# Embeddings are automatic - no manual step needed!

# Report
✓ Curator run complete: Labubu

Environment: local
Fetched: 10 items from PopMart World

Import Results:
  Created: 9 new entities
  Updated: 1 relationship
  Failed: 0 errors

Collection stats:
  Total items: 42
  With embeddings: 42
```

**Key differences from v1**:
- ✅ Fetch script simplified (~200 lines vs ~500)
- ✅ Import via MCP tools (not Python Supabase client)
- ✅ Semantic deduplication (not just external ID)
- ✅ Image localization via MCP (not Python)
- ✅ **Automatic embeddings** - text (create_entity) and image (localize_image) embeddings generated automatically
- ✅ Environment-specific secrets (local vs prod)

## Critical Principles

1. **Errors are normal** - Expect fetch scripts to fail on first run
2. **Debug autonomously** - Read errors, identify causes, fix immediately
3. **Iterate relentlessly** - Don't give up after one error, keep trying
4. **Fix, don't report** - Attempt fixes before declaring failure
5. **Use MCP for import** - You handle import via MCP tools, not Python
6. **Environment awareness** - Detect local vs prod, load correct secrets
7. **Report success** - Only declare completion after import actually succeeds

**You are not a passive script runner. You are an autonomous debugging agent that makes imports succeed through iteration and MCP tools.**

## Graph Import Workflow

When `fetched_data.json` contains hierarchical data (parents + children), follow this workflow:

### 1. Understand the Structure

```json
{
  "items": [
    // Parent entity (collection/series/set)
    {
      "name": "Monstress",
      "type": "collection",
      "external_ids": {"metron_series_id": "4733"},
      ...
    },
    // Child entities (cards/issues/items)
    {
      "name": "Monstress #1",
      "type": "comic",
      "external_ids": {"metron_id": "60339"},
      "parent": {
        "type": "collection",
        "external_ids": {"metron_series_id": "4733"}
      },
      "relationship": {
        "type": "contains",
        "order": 1
      },
      ...
    }
  ]
}
```

### 2. Import in Order (Parents First)

**Track parent entities in a cache:**
```python
parent_cache = {}  # Maps external_id_value → entity_id

for item in items:
    # Check if parent entity (no `parent` field)
    if not item.get('parent'):
        # It's a parent - check if exists
        existing_id = search_by_external_ids(item['external_ids'])

        if existing_id:
            # Parent exists - cache it
            for value in item['external_ids'].values():
                parent_cache[value] = existing_id
        else:
            # Create parent
            entity_id = create_entity(...)
            for value in item['external_ids'].values():
                parent_cache[value] = entity_id
    else:
        # It's a child - find parent first
        parent_id = resolve_parent(item['parent'], parent_cache)

        # Check if child exists
        existing_id = search_by_external_ids(item['external_ids'])

        if not existing_id:
            # Create child
            entity_id = create_entity(...)
        else:
            entity_id = existing_id

        # Create/update relationship
        create_relationship(
            from_id=parent_id,
            to_id=entity_id,
            type=item['relationship']['type'],
            order=item['relationship'].get('order')
        )
```

### 3. Parent Resolution

**To find parent by external_ids:**
```python
def resolve_parent(parent_ref, cache):
    # Check cache first
    for value in parent_ref['external_ids'].values():
        if value in cache:
            return cache[value]

    # Search database by external_ids (try each external ID)
    for key, value in parent_ref['external_ids'].items():
        result = search_by_external_id(
            external_id_key=key,
            external_id_value=value,
            entity_type=parent_ref['type']
        )
        # Found exact match
        if result and result['found'] > 0:
            entity_id = result['results'][0]['id']
            # Cache all external_id values for this entity
            for ext_value in parent_ref['external_ids'].values():
                cache[ext_value] = entity_id
            return entity_id

    return None
```

**This supports:**
- ✅ New parent entities (first import)
- ✅ Existing parent entities (subsequent imports)
- ✅ Multiple children linking to same parent
- ✅ Relationship ordering (issue_number, card_number, etc.)

## Command Variations

**Explicit slash command**:
```
/curator:run "Pokemon TCG"
/curator:run "Pokemon TCG" --fetch-only
/curator:run "Pokemon TCG" --import-only
/curator:run "Pokemon TCG" --env=prod
/curator:run "Pokemon TCG" --limit=50 --expansion="Base Set"
```

**Natural language** (you interpret and invoke):
```
"Import the latest Pokemon cards from Base Set"
→ Interpret as: /curator:run "Pokemon TCG" --expansion="Base Set"

"Fetch new LEGO Star Wars sets but don't import yet"
→ Interpret as: /curator:run "LEGO Sets" --theme="Star Wars" --fetch-only

"Update the Labubu collection in production"
→ Interpret as: /curator:run "Labubu" --env=prod
```

**Your job**: Parse user intent, extract curator name and arguments, execute workflow.
