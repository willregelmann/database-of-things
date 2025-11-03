---
name: pokemon-tcg-curator
description: Curate Pokémon Trading Card Game collections using the official Pokémon TCG API (pokemontcg.io). Use when importing Pokemon TCG sets, cards, and managing collection hierarchies with card images and metadata.
---

# Pokémon TCG Curator

## Overview

Curate your Pokémon Trading Card Game collection using the official Pokémon TCG API (pokemontcg.io). This skill discovers sets and cards, manages the collection hierarchy, and keeps your database synchronized with the latest TCG data.

**Works with**: `collectibles-manager` skill for database operations.

**Pokemon TCG Entity ID**: `55bc90fb-22e9-4715-bdde-2e004d0d5ee2`

## Quick Start

The skill manages a three-level hierarchy:
1. **Pokémon Trading Card Game** (trading_card_game) - Root entity
2. **Sets** (collection) - Named as `<series>[ - <expansion>]` (e.g., "Sword & Shield - Vivid Voltage")
3. **Cards** (trading_card) - Named as `<name> <number>/<total>` (e.g., "Charizard 025/185")

**Note on "Other" series**: In the pokemontcg.io data, "Other" is used as a catch-all category for sets that don't belong to a main series (e.g., McDonald's promos, special collections). The scripts automatically remove the "Other - " prefix from set names since it's not a real series designation.

All scripts use the Pokémon TCG API key from `.env` file.

### ⚠️ Standard Practice: Always Localize Images

**IMPORTANT**: After every import operation (whether single set or batch), immediately run image localization:

```bash
cd .claude/skills/collectibles-manager/scripts
python3 localize_images.py
```

This ensures:
- Images are stored in Supabase Storage (self-contained)
- No dependency on external URLs
- Downloads are spread out (helps with rate limiting)
- Better performance and reliability

### Setup

The skill uses the official [Pokemon TCG SDK](https://github.com/PokemonTCG/pokemon-tcg-sdk-python) and requires a virtual environment:

```bash
# Already set up! Virtual environment is at .claude/skills/pokemon-tcg-curator/venv/
# To reinstall dependencies if needed:
cd .claude/skills/pokemon-tcg-curator
venv/bin/pip install -r requirements.txt
```

**Running scripts**: Use the venv python:
```bash
cd .claude/skills/pokemon-tcg-curator/scripts
../venv/bin/python3 sync_sets.py --help
```

## Core Operations

### 0. Import from Local Data (Recommended!)

**⚡ FASTEST METHOD**: Use `scripts/import_from_data.py` to import from local JSON files instead of the API.

This is much faster, doesn't require API access, and works offline!

**Prerequisites**:
```bash
# Clone the pokemon-tcg-data repository (already done!)
cd .claude/skills/pokemon-tcg-curator
git clone https://github.com/PokemonTCG/pokemon-tcg-data.git data
```

**Usage:**
```bash
../venv/bin/python3 import_from_data.py [options]
```

**Options:**
- `--set <code>` - Import only specific set (e.g., "base1", "swsh4")
- `--sets-limit <n>` - Import only first N sets
- `--cards-limit <n>` - Import only first N cards per set
- `--dry-run` - Preview without making changes

**Examples:**
```bash
# Import all sets and all cards (fast!)
../venv/bin/python3 import_from_data.py

# Import just Base Set with all cards
../venv/bin/python3 import_from_data.py --set base1

# Import first 5 sets with first 20 cards each
../venv/bin/python3 import_from_data.py --sets-limit 5 --cards-limit 20

# Preview before importing
../venv/bin/python3 import_from_data.py --dry-run
```

**Updating the local data**:
```bash
cd data
git pull
```

---

### 1. Sync Sets (API Method)

Use `scripts/sync_sets.py` to discover and import Pokémon TCG sets from the API.

**Usage:**
```bash
../venv/bin/python3 sync_sets.py [--limit <n>] [--dry-run]
```

**Options:**
- `--limit <n>` - Process only first N sets (default: all)
- `--dry-run` - Preview what would be imported without making changes

**What it does:**
1. Fetches all sets from pokemontcg.io API
2. Checks which sets already exist (by external_id)
3. Creates new set entities with proper attributes
4. Links sets to "Pokémon Trading Card Game" with `contains` relationship
5. Updates existing sets if data changed

**Entity structure for sets:**
- `type`: "collection"
- `name`: "{series}[ - {name}]" (e.g., "Sword & Shield - Vivid Voltage")
- `year`: Release year (4-digit)
- `image_key`: Set logo URL (localized later)
- `attributes`:
  - `language`: "en"
  - `series`: Series name (e.g., "Sword & Shield")
  - `printedTotal`: Total cards in set
  - `total`: Total cards including secret rares
  - `releaseDate`: ISO date (YYYY-MM-DD)
- `external_ids`:
  - `pokemontcg.io`: Set code (e.g., "swsh4")

**Example:**
```bash
# Preview all sets
../venv/bin/python3 sync_sets.py --dry-run

# Import all sets
../venv/bin/python3 sync_sets.py

# Import only first 5 sets
../venv/bin/python3 sync_sets.py --limit 5
```

### 2. Sync Cards for a Set

Use `scripts/sync_cards.py` to discover and import cards for a specific set.

**Usage:**
```bash
../venv/bin/python3 sync_cards.py <set_name_or_code> [--limit <n>] [--dry-run]
```

**Arguments:**
- `<set_name_or_code>` - Set name (e.g., "Sword & Shield - Vivid Voltage") or API code (e.g., "swsh4")

**Options:**
- `--limit <n>` - Process only first N cards (default: all)
- `--dry-run` - Preview what would be imported without making changes

**What it does:**
1. Finds the set entity (by name or external_id)
2. Fetches all cards in the set from pokemontcg.io API
3. Checks which cards already exist (by external_id)
4. Creates new card entities with proper attributes
5. Links cards to set with `contains` relationship (order by card number)
6. Updates existing cards if data changed

**Entity structure for cards:**
- `type`: "trading_card"
- `name`: "{name} {number}/{total}" (e.g., "Charizard 025/185")
- `year`: Set release year
- `image_key`: High-res card image URL (localized later)
- `attributes`:
  - `language`: "en"
  - `card_number`: Full card number (e.g., "025/185")
  - `rarity`: Rarity tier (e.g., "Rare Holo", "Common")
  - `artist`: Illustrator name (when available)
- `external_ids`:
  - `pokemontcg.io`: Card ID (e.g., "swsh4-25")

**Examples:**
```bash
# Preview cards for a set
../venv/bin/python3 sync_cards.py "Sword & Shield - Vivid Voltage" --dry-run

# Import all cards for a set
../venv/bin/python3 sync_cards.py "Sword & Shield - Vivid Voltage"

# Use set code instead of name
../venv/bin/python3 sync_cards.py swsh4

# Import only first 10 cards
../venv/bin/python3 sync_cards.py swsh4 --limit 10
```

### 3. Sync Everything

Use `scripts/sync_all.py` to sync all sets and their cards in one command.

**Usage:**
```bash
../venv/bin/python3 sync_all.py [--sets-limit <n>] [--cards-limit <n>] [--dry-run]
```

**Options:**
- `--sets-limit <n>` - Process only first N sets (default: all)
- `--cards-limit <n>` - Process only first N cards per set (default: all)
- `--dry-run` - Preview what would be imported without making changes

**What it does:**
1. Syncs all sets first
2. For each set, syncs all cards
3. Shows progress and summary

**Examples:**
```bash
# Preview everything
../venv/bin/python3 sync_all.py --dry-run

# Sync all sets and all cards
../venv/bin/python3 sync_all.py

# Sync first 3 sets with first 10 cards each
../venv/bin/python3 sync_all.py --sets-limit 3 --cards-limit 10
```

### 4. Search TCG API

Use `scripts/search_api.py` to search the Pokémon TCG API without modifying your database.

**Usage:**
```bash
../venv/bin/python3 search_api.py <query_type> <query> [--limit <n>]
```

**Query types:**
- `card` - Search cards by name
- `set` - Search sets by name
- `artist` - Find cards by artist
- `type` - Find cards by type (e.g., "Fire", "Water")

**Examples:**
```bash
# Search for Charizard cards
../venv/bin/python3 search_api.py card Charizard

# Find all Base Set variations
../venv/bin/python3 search_api.py set "Base Set"

# Find cards illustrated by Ken Sugimori
../venv/bin/python3 search_api.py artist "Ken Sugimori" --limit 20

# Find all Fire-type cards
../venv/bin/python3 search_api.py type Fire --limit 10
```

### 5. Localize Images

**⚠️ IMPORTANT: Always localize images after importing sets/cards!**

After syncing sets and cards, localize all external images to Supabase Storage:

```bash
# From collectibles-manager skill (from project root)
cd .claude/skills/collectibles-manager/scripts
python3 localize_images.py
```

**Why localize images:**
- ✅ **Self-contained**: No dependency on external URLs
- ✅ **Performance**: Faster loading from local storage
- ✅ **Reliability**: Won't break if external sources change
- ✅ **Rate limiting**: Download process is throttled, helps avoid API limits
- ✅ **Bandwidth**: Reduces load on external image hosts

**Best practice**: Localize images immediately after each import batch (e.g., after importing each set or group of sets). This spreads out the download process and helps with rate limiting.

```bash
# Example: Import a set, then immediately localize its images
cd .claude/skills/pokemon-tcg-curator/scripts
../venv/bin/python3 import_from_data.py --set base1
cd ../../collectibles-manager/scripts
python3 localize_images.py
```

## Common Workflows

### Initial Setup - Import Entire Collection

**⚡ Recommended: Batched import with image localization**

For large imports, it's best to import in batches and localize images after each batch. This helps with:
- Rate limiting (spreads out downloads)
- Progress tracking (can resume if interrupted)
- Memory management (doesn't load everything at once)

```bash
# Strategy 1: Import sets in batches of 10, localizing after each batch
cd .claude/skills/pokemon-tcg-curator/scripts

# Import first 10 sets
../venv/bin/python3 import_from_data.py --sets-limit 10
cd ../../collectibles-manager/scripts
python3 localize_images.py

# Continue with more sets (adjust offset as needed)
cd ../../pokemon-tcg-curator/scripts
../venv/bin/python3 import_from_data.py --sets-limit 20  # Next 10 sets
cd ../../collectibles-manager/scripts
python3 localize_images.py

# Repeat until all sets imported...
```

**Alternative: Import everything at once (if time/bandwidth permits)**
```bash
cd .claude/skills/pokemon-tcg-curator/scripts

# 1. Import all sets and cards from local data
../venv/bin/python3 import_from_data.py

# 2. Localize all images (may take a while!)
cd ../../collectibles-manager/scripts
python3 localize_images.py

# 3. Verify the hierarchy
python3 list_hierarchy.py "Pokémon Trading Card Game" --max-depth 2
```

**Using API (slower, requires internet)**
```bash
cd .claude/skills/pokemon-tcg-curator/scripts

# 1. Sync sets and cards from API
../venv/bin/python3 sync_all.py --sets-limit 10  # Batch recommended

# 2. Localize images after each batch
cd ../../collectibles-manager/scripts
python3 localize_images.py

# 3. Repeat for more batches...
```

### Add a Specific Set

**⚡ Using local data (fast!)**
```bash
cd .claude/skills/pokemon-tcg-curator/scripts

# Import a specific set by code (e.g., base1, swsh4, sv3pt5)
../venv/bin/python3 import_from_data.py --set base1

# IMPORTANT: Immediately localize images after import
cd ../../collectibles-manager/scripts
python3 localize_images.py
```

**Using API**
```bash
cd .claude/skills/pokemon-tcg-curator/scripts

# 1. Search for the set first
../venv/bin/python3 search_api.py set "Scarlet & Violet"

# 2. Sync the set
../venv/bin/python3 sync_sets.py --dry-run  # Preview
../venv/bin/python3 sync_sets.py            # Import

# 3. Sync cards for that set
../venv/bin/python3 sync_cards.py "Scarlet & Violet 151"

# 4. IMPORTANT: Immediately localize images after import
cd ../../collectibles-manager/scripts
python3 localize_images.py
```

**💡 Pro tip**: For API imports, localizing images after each set helps spread out the download load and avoid hitting rate limits.

### Update Existing Data

The sync scripts check for existing entities and update them if data has changed:

```bash
cd .claude/skills/pokemon-tcg-curator/scripts

# Re-sync all sets (updates any changed data)
../venv/bin/python3 sync_sets.py

# Re-sync cards for a specific set
../venv/bin/python3 sync_cards.py "Base Set"

# If image URLs changed, re-localize
cd ../../collectibles-manager/scripts
python3 localize_images.py
```

**Note**: The localize_images.py script will skip images that are already localized (not external URLs), so it's safe to run after any update.

### Browse Your Collection

```bash
# Use collectibles-manager to browse
cd ../collectibles-manager

# See all sets
python3 scripts/search_entities.py --type collection

# See cards in a set
python3 scripts/list_hierarchy.py "Sword & Shield - Vivid Voltage"

# Search for specific cards
python3 scripts/search_entities.py --name Charizard --type trading_card
```

## API Rate Limits

The Pokémon TCG API has rate limits:
- **Without API key**: 20,000 requests/day, 1,000/hour
- **With API key** (recommended): 100,000 requests/day, 5,000/hour

All scripts include rate limiting and retry logic to avoid hitting limits.

**💡 Rate Limiting Strategy:**
- Import in batches (e.g., 10 sets at a time) instead of all at once
- Localize images after each batch to spread out downloads over time
- Image downloads from pokemontcg.io also count toward your bandwidth usage
- By localizing images incrementally, you reduce load spikes and avoid hitting rate limits

## Entity Naming Conventions

**Sets:**
- Format: `<series>[ - <expansion>]`
- Examples:
  - "Base Set" (no series)
  - "Sword & Shield - Vivid Voltage"
  - "Scarlet & Violet 151"
  - "Sun & Moon - Cosmic Eclipse"
  - "McDonald's Collection 2021" (note: "Other - " prefix removed)
  - "Southern Islands" (note: "Other - " prefix removed)

**Cards:**
- Format: `<name> <number>/<total>`
- Examples:
  - "Charizard 025/185"
  - "Pikachu 001/025"
  - "Professor's Research 178/185"

Numbers are zero-padded to 3 digits for proper sorting.

## External ID Format

**Sets:**
```json
{
  "pokemontcg.io": "swsh4"
}
```

**Cards:**
```json
{
  "pokemontcg.io": "swsh4-25"
}
```

These IDs are used to prevent duplicate imports and enable updates.

## Resources

### scripts/
Python scripts for TCG API operations:
- `sync_sets.py` - Sync sets from API
- `sync_cards.py` - Sync cards for a set
- `sync_all.py` - Sync everything
- `search_api.py` - Search TCG API
- `lib/api_client.py` - Pokémon TCG API client
- `lib/db_client.py` - Database operations

### references/
- `api_reference.md` - Pokémon TCG API documentation
- `naming_conventions.md` - Entity naming rules

All scripts support `--help` flag for detailed usage.
