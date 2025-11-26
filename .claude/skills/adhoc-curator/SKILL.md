---
name: adhoc-curator
description: Research and import collectibles via web search without predefined scripts. Use when user asks to find/discover/import items from the web.
---

# Ad-hoc Curator

You research and import collectibles via web search, without predefined fetch scripts.

## When to Use This Skill

Activate when user requests discovery-based imports:
- "Find all LEGO Star Wars sets from 2023 and add them"
- "Import the Pokemon Scarlet & Violet card list"
- "Add the Beanie Babies I found on this page"
- "What Marvel Legends figures came out in 2024? Add them to my collection"

**Do NOT use when:**
- A scripted curator already exists (use `run-curator` skill instead)
- User just wants to search/browse existing data (use MCP search tools)
- User wants to create a reusable curator (use `init-curator` skill)

## Phase 1: Initialize

**Acknowledge and create working directory:**

```bash
# Create timestamped working directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SLUG="<descriptive-slug>"  # e.g., "lego-star-wars-2023"
WORKDIR=".curator/adhoc/${TIMESTAMP}-${SLUG}"
mkdir -p "$WORKDIR"
```

**Start research notes:**

Create `$WORKDIR/research_notes.md`:
```markdown
# Ad-hoc Import: {description}

**Created:** {timestamp}
**Request:** {user's original request}

## Sources Consulted

(Will be filled during research)

## Decisions Made

(Will track any clarifications or choices)
```

**Tell the user:**
```
Starting ad-hoc import: {description}
Working directory: {WORKDIR}

I'll research this via web search, show you a sample for approval, then import.
```

## Phase 2: Research

### 2.1 Identify Sources

Use WebSearch to find authoritative sources:
1. **Official sources first** - manufacturer sites, official databases
2. **Collector databases** - Brickset, Bulbapedia, TCGPlayer, dedicated wikis
3. **Cross-reference** - verify data across multiple sources when uncertain

**Log sources in research_notes.md:**
```markdown
## Sources Consulted

- https://brickset.com/sets/year-2023/theme-Star-Wars (primary - set list)
- https://www.lego.com/en-us/themes/star-wars (images, official names)
```

### 2.2 Extract Data

Use WebFetch to extract structured data from each source.

**For each item, extract:**
- `name` - official name
- `type` - entity type (item, card, figure, etc.)
- `year` - release year
- `image_url` - best quality image available
- `source_url` - page where data was found (for attribution)
- `external_ids` - any identifiers (set number, card ID, SKU)
- `attributes` - relevant metadata (pieces, rarity, artist, etc.)

### 2.3 Build fetched_data.json

Write items incrementally to `$WORKDIR/fetched_data.json`:

```json
{
  "format_version": "1.0",
  "metadata": {
    "curator": "adhoc",
    "source": "web search",
    "fetched_at": "2024-01-15T12:00:00Z",
    "total_items": 47,
    "request": "LEGO Star Wars 2023 sets",
    "sources": [
      "https://brickset.com/...",
      "https://lego.com/..."
    ]
  },
  "items": [
    {
      "name": "Republic Attack Gunship",
      "type": "item",
      "year": 2023,
      "image_url": "https://...",
      "source_url": "https://brickset.com/sets/75354-1",
      "external_ids": {
        "lego_set_number": "75354"
      },
      "attributes": {
        "pieces": 3382,
        "theme": "Star Wars"
      }
    }
  ]
}
```

### 2.4 Handle Large Collections

For collections with 50+ items:
- Work in batches of ~25 items
- Save progress after each batch
- Report: "Found {N} items so far, continuing research..."
- If context gets tight, offer to pause: "I've found 150 items. Import now and continue, or keep going?"

### 2.5 When to Ask Questions

**Ask the user when:**
- Data conflicts between sources
- Scope is ambiguous ("Should I include promotional exclusives?")
- No reliable data found for an item
- Multiple interpretations of the request

**Record decisions in research_notes.md.**

## Phase 3: Collection Matching

Before import, determine where items should go.

### 3.1 Search Existing Collections

```
Use search_collectibles MCP tool:
  query: "{collection description}"
  entity_type: "collection"
  limit: 10
```

### 3.2 Decision Tree

**If strong match found (similarity > 0.90):**
- Use existing collection
- Report: "Found existing '{name}' collection"

**If partial match or hierarchy needed:**
- Propose structure: "I'd like to create: LEGO → Star Wars → 2023 Sets"
- Ask for confirmation

**If ambiguous:**
- Present options: "I found two possible parents: 'Star Wars LEGO' and 'LEGO Star Wars Sets'. Which should I use?"

**If no match and user hasn't specified:**
- Ask: "Where should these items go? I can create a new collection or add to an existing one."

### 3.3 Update fetched_data.json

Add parent references to items:
```json
{
  "name": "Republic Attack Gunship",
  "type": "item",
  "parent": {
    "type": "collection",
    "external_ids": {
      "adhoc_collection": "lego-star-wars-2023"
    }
  },
  "relationship": {
    "type": "contains",
    "order": 1
  },
  ...
}
```

## Phase 4: Sample Review

**Present summary and sample before importing:**

```
Research complete: 47 LEGO Star Wars 2023 sets

Sources:
- Brickset (set data, piece counts)
- LEGO.com (images, official names)

Sample items:
1. Republic Attack Gunship (75354) - 3382 pieces
2. Millennium Falcon (75375) - 921 pieces
3. AT-AT (75313) - 6785 pieces
4. X-Wing Starfighter (75355) - 1949 pieces
5. TIE Interceptor (75382) - 954 pieces

Full list: .curator/adhoc/{slug}/fetched_data.json

Does this look correct? Say 'yes' to import all 47 items, or let me know what needs adjustment.
```

**User options:**
- **Approve** → proceed to import
- **Request changes** → "Exclude sets under 500 pieces" → filter and re-present
- **View full list** → show all items from fetched_data.json
- **Abort** → stop without importing

## Phase 5: Import

**Once approved, use bulk import:**

```
Use bulk_import_curator_batch MCP tool:
  collection_id: {resolved parent collection ID}
  items: {contents of fetched_data.json items array}
  skip_duplicates: true
  localize_images: true
  generate_embeddings: true
  parallel_image_limit: 10
```

**Report results:**

```
Import complete: LEGO Star Wars 2023

Created: 45 new items
Skipped: 2 duplicates (already existed)
Images: 45/45 processed
Time: 38.5s

Collection: LEGO Star Wars → 2023 Sets
Working dir: .curator/adhoc/{slug}/
```

## Error Handling

### Conflicting Data
Ask user: "I found conflicting data for '{item}' - Source A says X, Source B says Y. Which should I use?"

### Missing Images
Import without image, report: "3 items imported without images (not found online)"

### Rate Limiting
Back off, try alternative sources. If stuck: "I'm being rate-limited. Should I continue with {alternative source} only, or wait and retry?"

### No Results
Report: "I couldn't find any '{query}' from reliable sources. Would you like me to try different search terms?"

### Large Collections
Offer checkpoints: "I've found 100+ items. Should I continue, or import what we have and do another pass?"

## Files Created

```
.curator/adhoc/{timestamp}-{slug}/
├── fetched_data.json    # Standard format, ready for bulk import
└── research_notes.md    # Sources, decisions, attribution trail
```

## After Import

- Files remain in `.curator/adhoc/` for reference
- User can delete if not needed
- If this becomes a recurring import, suggest creating a proper scripted curator with `init-curator`

## Key Principles

1. **Prioritize accuracy** - ask rather than guess when uncertain
2. **Show your work** - log sources and decisions in research_notes.md
3. **Sample before commit** - always show sample for approval
4. **Use existing tools** - leverage bulk_import_curator_batch, don't reinvent
5. **Fail gracefully** - missing images or data shouldn't block entire import
