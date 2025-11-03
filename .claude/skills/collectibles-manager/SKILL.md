---
name: collectibles-manager
description: Manage entities and relationships in a graph-based collectibles database using Supabase and PostgreSQL. Use when adding collectibles (cards, figures, etc.), creating collections, building hierarchies, searching items, bulk importing data, or localizing external images to storage. Provides abstract helper commands instead of raw SQL.
---

# Collectibles Manager

## Overview

Manage a graph-based collectibles database with entities (cards, collections, franchises) and relationships (contains, variant_of, part_of). Execute common database operations through Python helper scripts instead of writing SQL directly.

## Quick Start

The database uses a pure graph model with two tables:
- **entities** - Everything: franchises, games, collections, cards, figures, etc.
- **relationships** - Connections between entities (parent→child direction)

All helper scripts connect to the database via Docker:
```bash
docker exec supabase_db_database-of-things psql -U postgres
```

Reference `references/schema.md` for complete database schema documentation.

## Core Operations

### 1. Add a Single Entity

Use `scripts/add_entity.py` to add franchises, collections, cards, or any collectible.

**Required fields:**
- `--type` - Entity type (e.g., `collection`, `trading_card`, `franchise`)
- `--name` - Display name

**Optional fields:**
- `--year` - Year (integer)
- `--country` - ISO country code (2 characters)
- `--language` - ISO 639-1 language code (2 characters, e.g., `en`, `ja`, `es`)
- `--image-key` - Image URL or storage path
- `--attributes` - JSON object with additional metadata

**Examples:**

```bash
# Add a collection
python scripts/add_entity.py --type collection --name "Base Set" --year 1999 --country US

# Add a card with attributes
python scripts/add_entity.py \
  --type trading_card \
  --name "Charizard 4/102" \
  --year 1999 \
  --country US \
  --language en \
  --image-key "https://images.pokemontcg.io/base1/4.png" \
  --attributes '{"rarity": "rare", "hp": 120, "card_number": "4/102"}'

# Add a franchise
python scripts/add_entity.py --type franchise --name "Star Wars" --year 1977
```

### 2. Create Relationships

Use `scripts/add_relationship.py` to connect entities in parent→child direction.

**Required fields:**
- `--from` - Parent entity name
- `--to` - Child entity name
- `--type` - Relationship type (`contains`, `variant_of`, `part_of`)

**Optional fields:**
- `--order` - Sort order (integer, for ordering items in collections)
- `--attributes` - JSON object with additional metadata

**Examples:**

```bash
# Collection contains card
python scripts/add_relationship.py \
  --from "Base Set" \
  --to "Charizard 4/102" \
  --type contains

# With ordering
python scripts/add_relationship.py \
  --from "Base Set" \
  --to "Bulbasaur 1/102" \
  --type contains \
  --order 1

# Variant relationship
python scripts/add_relationship.py \
  --from "Charizard 1st Edition" \
  --to "Charizard" \
  --type variant_of
```

**Relationship Types:**
- `contains` - Parent contains child (most common for collections)
- `variant_of` - Alternative version points to base version
- `part_of` - Component points to whole item

### 3. Search for Entities

Use `scripts/search_entities.py` to find entities by name or type.

**Options:**
- `--name` - Case-insensitive partial match
- `--type` - Filter by entity type
- `--limit` - Maximum results (default: 50)

**Examples:**

```bash
# Search by name
python scripts/search_entities.py --name Charizard

# Find all collections
python scripts/search_entities.py --type collection

# Combined search with limit
python scripts/search_entities.py --name Pokemon --type trading_card --limit 10
```

### 4. Semantic Search (Vector Similarity)

Use `scripts/semantic_search.py` to find entities by meaning rather than exact text matches. Powered by AI embeddings, this searches based on semantic similarity.

**Options:**
- `query` - Natural language search query (required)
- `--limit` - Maximum results (default: 20)
- `--type` - Filter by entity type
- `--model` - Sentence-transformer model (default: all-MiniLM-L6-v2)

**Examples:**

```bash
# Find entities related to "fire dragon pokemon"
python scripts/semantic_search.py "fire dragon pokemon"

# Find similar collections
python scripts/semantic_search.py "base set" --type collection

# Limit results
python scripts/semantic_search.py "electric mouse" --limit 10

# Exact card search with semantic ranking
python scripts/semantic_search.py "charizard" --type trading_card
```

**How it works:**
- Converts your query into a 384-dimensional vector using AI
- Compares against pre-computed embeddings for all entities
- Returns results ranked by semantic similarity (0-100%)
- Uses HNSW index for fast similarity search

**Similarity Scoring:**
- 🟢 Green (80%+): Very strong match
- 🟡 Yellow (60-79%): Good match
- 🔴 Red (<60%): Weak match

**Use cases:**
- Find items by description ("legendary bird pokemon")
- Discover related items without knowing exact names
- Handle typos and variations automatically
- Search across languages (if embeddings trained multilingually)

**First-time setup:**
```bash
# Install dependencies (one-time)
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install sentence-transformers

# Generate embeddings for all entities (run after adding new entities)
python scripts/generate_embeddings.py
```

**REST API:**

Semantic search is available via Supabase's REST API using the `search_by_text` RPC function:

```bash
# Find Charizard cards
curl -X POST 'http://127.0.0.1:54321/rest/v1/rpc/search_by_text' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "charizard",
    "entity_type_filter": "trading_card",
    "result_limit": 5
  }'

# Find fire-type Pokemon
curl -X POST 'http://127.0.0.1:54321/rest/v1/rpc/search_by_text' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "fire pokemon",
    "entity_type_filter": "trading_card"
  }'

# Find base set collections
curl -X POST 'http://127.0.0.1:54321/rest/v1/rpc/search_by_text' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "base",
    "entity_type_filter": "collection",
    "result_limit": 10
  }'
```

**Parameters:**
- `query_text` (required) - Natural language search query
- `entity_type_filter` (optional) - Filter by entity type (e.g., "trading_card", "collection")
- `result_limit` (optional) - Maximum results (default: 20)

**Response format:**
```json
[
  {
    "id": "uuid-here",
    "name": "Charizard 4/102",
    "type": "trading_card",
    "year": 1999,
    "country": null,
    "language": "en",
    "image_key": "images/...",
    "attributes": {...},
    "similarity": 1.0
  }
]
```

**From JavaScript/TypeScript:**
```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient('http://127.0.0.1:54321', 'YOUR_ANON_KEY')

const { data, error } = await supabase.rpc('search_by_text', {
  query_text: 'fire dragon pokemon',
  entity_type_filter: 'trading_card',
  result_limit: 10
})
```

### 5. Display Hierarchy

Use `scripts/list_hierarchy.py` to visualize entity relationships.

**Usage:**
```bash
python list_hierarchy.py <entity_name> [--max-depth <n>] [--reverse]
```

**Options:**
- `--max-depth` - Limit traversal depth
- `--reverse` - Show parents instead of children (go up the tree)

**Examples:**

```bash
# Show what a franchise contains
python scripts/list_hierarchy.py "Pokémon"

# Limit depth
python scripts/list_hierarchy.py "Pokémon" --max-depth 2

# Show what contains a specific card (reverse)
python scripts/list_hierarchy.py "Bulbasaur 001/165" --reverse
```

**Output format:**
```
⬇️  Hierarchy under: Pokémon

Pokémon (franchise)
  └─ Pokémon Trading Card Game (trading_card_game)
    └─ Scarlet & Violet - 151 (collection)
      └─ Bulbasaur 001/165 (trading_card)
```

### 5. Bulk Import

Use `scripts/bulk_import.py` to import multiple entities and relationships from JSON.

**Usage:**
```bash
python scripts/bulk_import.py <json_file>
```

**JSON Format:**
See `assets/bulk_import_template.json` for a complete template.

```json
{
  "entities": [
    {
      "name": "Collection Name",
      "type": "collection",
      "year": 2023,
      "country": "US",
      "language": "en",
      "image_key": "https://example.com/image.jpg",
      "attributes": {
        "total_cards": 102,
        "set_code": "example1"
      }
    }
  ],
  "relationships": [
    {
      "from": "Collection Name",
      "to": "Card Name",
      "type": "contains",
      "order": 1,
      "attributes": {}
    }
  ]
}
```

**Example workflow:**

1. Copy the template:
   ```bash
   cp assets/bulk_import_template.json my_collection.json
   ```

2. Edit `my_collection.json` with your data

3. Import:
   ```bash
   python scripts/bulk_import.py my_collection.json
   ```

**Output:**
```
📦 Importing 3 entities...
  ✅ 1/3: Example Collection
  ✅ 2/3: Example Card 1/102
  ✅ 3/3: Example Card 2/102

✅ Imported 3/3 entities

🔗 Importing 2 relationships...
  ✅ 1/2: Example Collection -> Example Card 1/102
  ✅ 2/2: Example Collection -> Example Card 2/102

✅ Imported 2/2 relationships
```

### 6. Localize External Images

Use `scripts/localize_images.py` to download external images and store them in Supabase Storage.

This is useful when you have entities with external image URLs (e.g., from Pokémon TCG API, Wikipedia) and want to store them locally.

**Usage:**
```bash
python scripts/localize_images.py [--dry-run] [--limit <n>]
```

**Options:**
- `--dry-run` - Preview what would be downloaded without making changes
- `--limit <n>` - Process only first N images

**What it does:**
1. Finds all entities with external image URLs (starting with `http://` or `https://`)
2. Downloads each image
3. Uploads to Supabase Storage as `images/<entity_id>.<extension>`
4. Updates the entity's `image_key` to the new storage path

**Examples:**

```bash
# Preview changes first
python scripts/localize_images.py --dry-run

# Download and store all external images
python scripts/localize_images.py

# Process only the first 5 images
python scripts/localize_images.py --limit 5
```

**Output:**
```
🔍 Finding entities with external images...
📦 Found 6 entities with external images

[1/6] Bulbasaur 001/165
  URL: https://dz3we2x72f7ol.cloudfront.net/expansions/151/en-us/SV3pt5_EN_1.png
  ⬇️  Downloading...
  ⬆️  Uploading to storage...
  💾 Updating entity...
  ✅ Success: images/a22ebb98-878b-4a6c-a53b-051da25eef60.png

✅ Successfully localized 6/6 images
```

**Benefits:**
- Faster loading (images served from your own storage)
- Reliability (no dependency on external URLs)
- Control (images won't disappear if external sites change)
- Transformations (can use Supabase image resizing)

## Common Workflows

### Adding a Complete Collection

When adding an entire collection (e.g., Pokémon Base Set with 102 cards):

1. **Create the collection entity:**
   ```bash
   python scripts/add_entity.py \
     --type collection \
     --name "Base Set" \
     --year 1999 \
     --attributes '{"total_cards": 102}'
   ```

2. **Prepare bulk import JSON:**
   - Use `assets/bulk_import_template.json` as starting point
   - List all cards in `entities` array
   - Create `contains` relationships for each card

3. **Import:**
   ```bash
   python scripts/bulk_import.py base_set.json
   ```

4. **Verify:**
   ```bash
   python scripts/list_hierarchy.py "Base Set"
   ```

### Connecting to Existing Hierarchy

To add items to an existing hierarchy:

1. **Search for parent entity:**
   ```bash
   python scripts/search_entities.py --name "Scarlet & Violet"
   ```

2. **Add new child entity:**
   ```bash
   python scripts/add_entity.py --type trading_card --name "New Card"
   ```

3. **Create relationship:**
   ```bash
   python scripts/add_relationship.py \
     --from "Scarlet & Violet - 151" \
     --to "New Card" \
     --type contains
   ```

### Managing Variants

For cards with multiple versions (1st Edition, Shadowless, etc.):

1. **Add base card:**
   ```bash
   python scripts/add_entity.py --type trading_card --name "Charizard"
   ```

2. **Add variant:**
   ```bash
   python scripts/add_entity.py \
     --type trading_card \
     --name "Charizard 1st Edition" \
     --attributes '{"variant": "1st_edition"}'
   ```

3. **Link variant to base:**
   ```bash
   python scripts/add_relationship.py \
     --from "Charizard 1st Edition" \
     --to "Charizard" \
     --type variant_of
   ```

## Database Schema

For complete schema details including:
- Table structures and columns
- Relationship types and directions
- Common JSONB attribute patterns
- Image storage patterns
- Helper SQL functions

Refer to `references/schema.md`.

## Resources

### scripts/
Python helper commands for database operations:
- `add_entity.py` - Add single entity
- `add_relationship.py` - Create relationships
- `search_entities.py` - Search by name/type
- `semantic_search.py` - AI-powered semantic search (requires sentence-transformers)
- `generate_embeddings.py` - Generate vector embeddings for semantic search
- `list_hierarchy.py` - Display hierarchical structure
- `bulk_import.py` - Import from JSON
- `localize_images.py` - Download external images to Supabase Storage

All scripts are executable and include `--help` flag for detailed usage.

### references/
- `schema.md` - Complete database schema documentation

### assets/
- `bulk_import_template.json` - Template for bulk imports
