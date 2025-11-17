# Curator System User Guide

This guide covers essential workflows for using the v2 curator system to import collectibles data.

## What is a Curator?

A curator is an automated agent that fetches collectibles data from external sources and imports it into the database. Each curator is specialized for a specific collection (e.g., Pokemon TCG, Power Rangers Toys).

**Key Features**:
- AI-driven: Claude autonomously handles fetch errors, deduplication, and import
- Multi-environment: Separate local and production database support
- Natural language: Use slash commands or plain English
- Semantic deduplication: Finds duplicates by meaning, not just exact text

## Quick Start

### Creating Your First Curator

```bash
# Use the init command - it will ask you questions
/curator:init "Pokemon TCG"
```

**What happens**:
1. Claude asks about your collection (Socratic method)
2. Checks Terms of Service for compliance
3. Generates fetch script (~200 lines)
4. Creates config files
5. Sets up secrets templates

**Example interaction**:
```
Claude: What items belong in this collection?
You: Pokemon trading cards from all sets and expansions

Claude: Where does the data come from?
You: The Pokemon TCG API at pokemontcg.io

Claude: What makes items unique?
You: Card ID from the API

[Claude generates fetch_data.py, config.json, README.md, secrets templates]
```

**Output structure**:
```
.curator/curators/Pokemon TCG/
├── README.md                        # Complete documentation
├── config.json                      # Curator configuration (v2 format)
├── scripts/
│   └── fetch_data.py                # Data fetching script
├── secrets.env.example              # API key template
├── secrets.local.env.example        # Local collection ID template
└── secrets.prod.env.example         # Production collection ID template
```

### Running an Existing Curator

```bash
# Fetch and import data
/curator:run "Labubu"

# Or use natural language
"Import the latest Labubu figures"
```

**What happens**:
1. Detects environment (local vs production)
2. Loads secrets (API keys, collection ID)
3. Runs fetch script (may auto-fix errors)
4. Imports via MCP tools:
   - Searches for duplicates (semantic search)
   - Creates new entities
   - Links images
   - Generates embeddings
5. Reports results

**Example output**:
```
Environment: local
MCP Server: database-of-things-local

Fetching items from PopMart World...
✓ Fetched 10 items → fetched_data.json

Import Results:
  [1/10] ✓ Created: Labubu Original (Series 1)
  [2/10] ✓ Created: Labubu Macaron (Series 1)
  [3/10] ↻ Updated: Labubu Strawberry (already exists)
  ...
  [10/10] ✓ Created: Labubu Winter (Series 2)

Generating embeddings for 9 new entities...

✓ Curator run complete: Labubu

Import Results:
  Created: 9 new entities
  Updated: 1 relationship
  Failed: 0 errors

Collection stats:
  Total items: 42
  With embeddings: 42
```

## Understanding Secrets

Curators use a two-file secrets pattern for multi-environment support:

### API Keys (Shared Across Environments)

**File**: `secrets.env`

```bash
# Pokemon TCG Curator - Shared Configuration
# Copy from secrets.env.example

# Pokemon TCG API Key (get from https://pokemontcg.io)
POKEMON_TCG_API_KEY=your_api_key_here
```

**Purpose**: API credentials used for fetching data, same across all environments.

### Collection IDs (Environment-Specific)

**File**: `secrets.local.env` (for local Supabase)

```bash
# Pokemon TCG Collection - Local Development
# Copy from secrets.local.env.example

# Get this by creating the collection in local Supabase:
# psql: INSERT INTO entities (name, type) VALUES ('Pokemon TCG', 'collection') RETURNING id;
COLLECTION_ID=abc-123-local-uuid
```

**File**: `secrets.prod.env` (for production Supabase)

```bash
# Pokemon TCG Collection - Production
# Copy from secrets.prod.env.example

# Get this by creating the collection in production Supabase
COLLECTION_ID=xyz-789-prod-uuid
```

**Why separate?**: Your local and production databases are different instances with different UUIDs. This pattern lets you test locally without touching production.

### Setting Up Secrets

1. **Copy the templates**:
   ```bash
   cd .curator/curators/Pokemon\ TCG/
   cp secrets.env.example secrets.env
   cp secrets.local.env.example secrets.local.env
   ```

2. **Get an API key** (if required):
   - Visit the data source's developer portal
   - Register for an API key
   - Paste into `secrets.env`

3. **Create collection in database**:
   ```bash
   # Start local Supabase
   ./bin/supabase start

   # Access PostgreSQL
   docker exec -it supabase_db_database-of-things psql -U postgres -d postgres

   # Create collection
   INSERT INTO entities (name, type) VALUES ('Pokemon TCG', 'collection') RETURNING id;
   # Copy the UUID it returns

   # Paste into secrets.local.env
   COLLECTION_ID=<paste-uuid-here>
   ```

4. **Test the fetch**:
   ```bash
   cd .curator/curators/Pokemon\ TCG/
   source secrets.env
   source secrets.local.env
   python3 scripts/fetch_data.py --limit=5
   ```

## Advanced Workflows

### Fetch Only (No Import)

Use when you want to inspect data before importing:

```bash
/curator:run "Pokemon TCG" --fetch-only

# Check the output
cat .curator/curators/Pokemon\ TCG/fetched_data.json | jq '.metadata'
```

**When to use**:
- Testing a new fetch script
- Previewing data structure
- Checking for API errors

### Import Only (Skip Fetch)

Use when you already have `fetched_data.json`:

```bash
/curator:run "Pokemon TCG" --import-only
```

**When to use**:
- Re-importing after fixing data issues
- Testing import logic without re-fetching
- Importing manually curated data

### Environment Switching

Default is local, but you can target production:

```bash
/curator:run "Labubu" --env=prod
```

**Requirements**:
- Production MCP server configured in `.mcp.json`
- `secrets.prod.env` with production collection ID
- Production database accessible

### Filtering Data

Pass filters to fetch scripts:

```bash
# For Pokemon TCG (if fetch script supports --set filter)
/curator:run "Pokemon TCG" --set="Base Set" --limit=50

# Natural language works too
"Import 50 cards from Pokemon Base Set"
```

**How it works**: Claude parses your request and passes arguments to the fetch script.

### Checking Status

```bash
/curator:status "Labubu"
```

**Output**:
```
Collection: Labubu
Items: 42
Last import: 2025-11-15 14:30 UTC
With embeddings: 42 (100%)
```

## Common Tasks

### Updating an Existing Collection

Just re-run the curator - it will deduplicate automatically:

```bash
/curator:run "Power Rangers Toys"
```

**What happens**:
- Fetches latest data
- Searches for each item by name (semantic search)
- If similarity > 95%: Links to existing entity
- If no match: Creates new entity

**Result**: New items added, existing items preserved.

### Re-fetching with Different Filters

```bash
# First run: Base Set
/curator:run "Pokemon TCG" --set="Base Set"

# Second run: Jungle Set
/curator:run "Pokemon TCG" --set="Jungle"
```

Both sets will coexist in the collection.

### Testing Before Production

```bash
# 1. Test locally with small limit
/curator:run "Pokemon TCG" --limit=10

# 2. Check results in Studio UI
# http://127.0.0.1:54323

# 3. If good, run on production
/curator:run "Pokemon TCG" --env=prod
```

### Handling Errors

Claude autonomously fixes most errors. If fetch fails:

**Missing dependency**:
```
Error: ModuleNotFoundError: No module named 'requests'
→ Claude runs: pip install requests
→ Retries fetch automatically
```

**Invalid API key**:
```
Error: 401 Unauthorized
→ Claude prompts: "Check API key in secrets.env"
→ You fix it, re-run curator
```

**API structure changed**:
```
Error: KeyError: 'items'
→ Claude edits fetch script to match new API structure
→ Retries fetch automatically
```

**When Claude can't fix**: You'll get clear error message with suggested fixes.

## Real Examples

### Example 1: Labubu (No API Key Required)

Labubu curator scrapes from PopMart World (no authentication):

```bash
# Run it
/curator:run "Labubu" --limit=5

# What happens:
# 1. Scrapes popmartworld.com/collections
# 2. Parses HTML for series and figures
# 3. Downloads images to Supabase storage
# 4. Creates entities with semantic deduplication
# 5. Generates embeddings
```

**Fetch output** (`fetched_data.json`):
```json
{
  "format_version": "1.0",
  "metadata": {
    "curator": "Labubu",
    "source": "https://www.popmartworld.com/collections/labubu",
    "fetched_at": "2025-11-15T10:30:00Z",
    "total_items": 5
  },
  "items": [
    {
      "name": "Labubu Original",
      "type": "figure",
      "year": 2023,
      "image_url": "https://cdn.popmartworld.com/...",
      "source_url": "https://www.popmartworld.com/products/labubu-original",
      "external_ids": {
        "popmart_sku": "LABU-001"
      },
      "attributes": {
        "series": "Series 1",
        "size": "2.8 inches"
      }
    }
  ]
}
```

**For hierarchical data** (collections → items), use graph structure:
```json
{
  "format_version": "1.0",
  "metadata": {
    "curator": "American Comics",
    "source": "https://metron.cloud",
    "fetched_at": "2025-11-16T07:29:33Z",
    "total_items": 3
  },
  "items": [
    {
      "name": "Monstress",
      "type": "collection",
      "year": 2015,
      "external_ids": {
        "metron_series_id": "4733"
      },
      "attributes": {
        "publisher": "Image Comics"
      }
    },
    {
      "name": "Monstress #1",
      "type": "comic",
      "year": 2015,
      "external_ids": {
        "metron_id": "60339"
      },
      "image_url": "https://static.metron.cloud/media/issue/...",
      "source_url": "https://metron.cloud/issue/60339/",
      "parent": {
        "type": "collection",
        "external_ids": {
          "metron_series_id": "4733"
        }
      },
      "relationship": {
        "type": "contains",
        "order": 1
      },
      "attributes": {
        "issue_number": "1",
        "publisher": "Image Comics",
        "writers": ["Marjorie Liu"],
        "artists": ["Sana Takeda"]
      }
    }
  ]
}
```

The import workflow handles this automatically:
1. **Parent entities** (no `parent` field) are created/found first
2. **Child entities** reference parents via `external_ids` for lookup
3. **Relationships** are created with type and optional order
4. This supports both new and existing parent collections

### Example 2: Power Rangers Toys (No API Key Required)

Power Rangers curator scrapes from grnrngr.com:

```bash
/curator:run "Power Rangers Toys" --limit=3

# Fetches toy listings with images
# Creates entities for Megazords, Zords, action figures
# Links components (e.g., Red Ranger Zord is component of Megazord)
```

### Example 3: Pokemon TCG (Requires API Key)

Pokemon TCG curator uses pokemontcg.io API:

```bash
# 1. Get API key from https://pokemontcg.io
# 2. Add to secrets.env:
#    POKEMON_TCG_API_KEY=your_key_here
# 3. Run curator:

/curator:run "Pokemon TCG" --set="Base Set" --limit=20

# Fetches 20 cards from Base Set
# Deduplicates by pokemontcg.io ID
# Falls back to semantic search if ID missing
```

## Troubleshooting

### Curator Not Found

```
Error: Curator not found: Pokemon TCG
Available curators:
  American Comics
  Labubu
  ...
```

**Fix**: Check exact name (case-sensitive), or create with `/curator:init`.

### Collection ID Not Set

```
Error: COLLECTION_ID not set in secrets.local.env
```

**Fix**: Create collection in database, paste UUID into secrets file (see "Setting Up Secrets" above).

### API Rate Limit

```
Error: 429 Too Many Requests
→ Waiting 2s...
✓ Retry successful
```

**Fix**: Claude handles this automatically with exponential backoff.

### Fetch Script Fails

If fetch consistently fails:

1. **Check secrets**: `cat secrets.env` (is API key valid?)
2. **Run manually**: `python3 scripts/fetch_data.py --limit=1`
3. **Read error**: Error message will show exact issue
4. **Edit script**: Fix the issue in `scripts/fetch_data.py`
5. **Re-run curator**: `/curator:run "Collection Name"`

### Import Failures

```
Import Results:
  Created: 8
  Updated: 1
  Failed: 1 errors
```

**Fix**: Check error messages in output, common issues:
- Image URL 404 → Logged as warning, entity created without image
- Duplicate relationship → Logged as "updated", not an error
- Invalid attributes → Fix in fetch script's `normalize_item()` function

## Tips

1. **Start small**: Use `--limit=10` when testing
2. **Test locally first**: Debug with local data before production
3. **Check fetched_data.json**: Inspect output before importing
4. **Use semantic search**: Trust the 0.95+ similarity threshold
5. **Let Claude debug**: Don't manually fix errors - let it iterate
6. **Monitor storage**: Images consume space - plan accordingly

## Next Steps

- **For technical details**: See `docs/curator-technical-reference.md`
- **For agent instructions**: See `CLAUDE.md` (if you're Claude)
- **For schema info**: See `CLAUDE.md` (Database Architecture section)
