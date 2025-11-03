---
name: video-game-curator
description: Curate video game collections using the MobyGames API. Discovers games across 300+ platforms with proper differentiation for paired releases (Pokémon Sword vs Shield, Red vs Blue) and region-specific versions. Includes high-quality scanned box art, UPC/SKU tracking, and comprehensive metadata. Perfect for physical game collectibles.
---

# Video Game Curator

## Overview

Curate your video game collection using the MobyGames API. This skill discovers games across 300+ platforms, manages collections and franchises, and keeps your database synchronized with comprehensive gaming metadata.

**Perfect for collectibles tracking**: MobyGames properly differentiates between paired releases (Pokémon Sword vs Shield, Red vs Blue) and tracks region-specific versions with UPC/SKU information.

**Works with**: `collectibles-manager` skill for database operations.

## Data Sources

### MobyGames API (Currently Implemented) ⭐
- **Paid** ($5/month for personal use, $10/month for commercial)
- **Most comprehensive** video game database (since 1979)
- 300,000+ games across 300+ platforms
- **Proper differentiation**: Separate entries for Sword vs Shield, Red vs Blue, etc.
- **Region-specific releases**: NA, EU, JP releases tracked separately
- **UPC/SKU tracking**: Different editions and versions properly cataloged
- **Scanned box art**: High-quality scans of actual physical game boxes by country
- **Publisher/Developer by release**: Tracks who published/developed each regional release
- **Best for collectibles**: Perfect for tracking physical games with cover art and metadata
- Detailed company/developer/publisher information

**Get API key**: https://www.mobygames.com/info/api/

**Rate limiting**: 720 requests per hour (~5 seconds between requests, strictly enforced)

## Quick Start

The skill manages a flexible hierarchy:
1. **Franchises** (franchise) - Root entities for game series (e.g., "The Legend of Zelda", "Final Fantasy")
2. **Collections/Series** (collection) - Game series or collections (e.g., "Mario Kart", "Dark Souls")
3. **Games** (video_game) - Individual games (e.g., "The Legend of Zelda: Breath of the Wild")
4. **Editions/Versions** (video_game) - Special editions, remasters, ports

**Note**: Games can belong to multiple collections and platforms. Use relationships to model this flexibility.

All scripts require a MobyGames API key from: https://www.mobygames.com/info/api/

### Setup

The skill uses the standard `requests` library and requires a virtual environment:

```bash
# Create virtual environment
cd .claude/skills/video-game-curator
python3 -m venv venv

# Install dependencies
venv/bin/pip install -r requirements.txt

# Add API key to .env
echo "MOBY_GAMES_API_KEY=your_api_key_here" >> ../../../.env
```

**Running scripts**: Use the venv python:
```bash
cd .claude/skills/video-game-curator/scripts
../venv/bin/python3 search_api.py --help
```

## Core Operations

### 1. Search Games

Use `scripts/search_api.py` to search the MobyGames API without modifying your database.

**Usage:**
```bash
../venv/bin/python3 search_api.py <query> [--limit <n>] [--platform <id>]
```

**Options:**
- `<query>` - Game name to search for (case-sensitive, supports partial matches)
- `--limit <n>` - Number of results (default: 20, max: 100)
- `--platform <id>` - Filter by platform ID (single platform only)
  - Common platform IDs: `203` (Nintendo Switch), `10` (Game Boy), `81` (PlayStation 4), `4` (PC)

**Examples:**
```bash
# Search for Pokemon Sword (note: use exact accents)
../venv/bin/python3 search_api.py "Pokémon Sword"

# Search Nintendo Switch games only
../venv/bin/python3 search_api.py "Zelda" --platform 203

# Get top 10 results
../venv/bin/python3 search_api.py "Final Fantasy" --limit 10
```

**Important**: MobyGames search is case-sensitive and requires proper accents (é in Pokémon).

### 2. Import a Game

Use `scripts/sync_game.py` to import a specific game by its MobyGames ID or name.

**Usage:**
```bash
../venv/bin/python3 sync_game.py <game_id_or_name> [--platform <id>] [--dry-run] [--franchise <name>]
```

**Arguments:**
- `<game_id_or_name>` - MobyGames game ID (numeric) or game name (will search)

**Options:**
- `--platform <id>` - Platform ID to import (if game is on multiple platforms)
- `--dry-run` - Preview what would be imported without making changes
- `--franchise <name>` - Create/link to franchise entity

**What it does:**
1. Fetches game data from MobyGames API
2. Gets platform-specific release information
3. Identifies NA release (or first release if NA not found)
4. Extracts developer and publisher from release data
5. Creates game entity with simplified attributes
6. Optionally creates/links to franchise
7. Updates existing games if data changed

**Entity structure for games:**
- `type`: "video_game"
- `name`: Game title (e.g., "Pokémon Sword")
- `year`: Release year
- `language`: Language code (e.g., "en", "es", "fr") - defaults to "en" (dedicated column)
- `image_url`: null (MobyGames doesn't provide images in API)
- `attributes`:
  - `region`: Region code (e.g., "na", "eu", "jp") - defaults to "na"
  - `platform`: Platform name (e.g., "Nintendo Switch", "Game Boy")
  - `developer`: Developer (e.g., "Game Freak, Inc.")
  - `publisher`: Publisher (e.g., "Nintendo of America Inc.")
- `external_ids`:
  - `mobygames`: MobyGames game ID (numeric)

**Examples:**
```bash
# Preview importing a game by ID
../venv/bin/python3 sync_game.py 137306 --dry-run

# Import Pokémon Sword
../venv/bin/python3 sync_game.py 137306

# Import by name (will search first)
../venv/bin/python3 sync_game.py "Pokémon Sword"

# Import specific platform version
../venv/bin/python3 sync_game.py 137306 --platform 203

# Import and link to franchise
../venv/bin/python3 sync_game.py 137306 --franchise "Pokémon"
```

### 3. Create Franchises and Collections

Manually create franchise and collection entities using the `collectibles-manager` skill:

```bash
cd ../collectibles-manager/scripts

# Create franchise
../venv/bin/python3 create_entity.py \
  --type franchise \
  --name "The Legend of Zelda" \
  --year 1986 \
  --attributes '{"developer": "Nintendo", "description": "Action-adventure game series"}'

# Create collection/series
../venv/bin/python3 create_entity.py \
  --type collection \
  --name "Dark Souls Series" \
  --year 2011 \
  --attributes '{"developer": "FromSoftware", "genre": "Action RPG"}'
```

### 4. Link Games to Collections

After importing games, create relationships:

```bash
cd ../collectibles-manager/scripts

# Link game to franchise
../venv/bin/python3 create_relationship.py \
  --from-name "Pokémon" \
  --to-name "Pokémon Sword" \
  --type contains

# Link game to series
../venv/bin/python3 create_relationship.py \
  --from-name "Pokémon Generation 8" \
  --to-name "Pokémon Sword" \
  --type contains \
  --attributes '{"order": 1}'
```

## Common Workflows

### Import a Franchise

**Example: Import Legend of Zelda games**

```bash
# 1. Search for games first
../venv/bin/python3 search_api.py "zelda" --limit 20

# 2. Import multiple games
../venv/bin/python3 sync_games.py --search "zelda" --limit 15 --franchise "The Legend of Zelda"

# 3. Verify the hierarchy
cd ../collectibles-manager/scripts
../venv/bin/python3 list_hierarchy.py "The Legend of Zelda" --max-depth 2
```

### Import a Platform's Games

**Example: Import Nintendo Switch exclusives**

```bash
# Platform ID 7 is Nintendo Switch
../venv/bin/python3 sync_games.py --search "exclusive" --platforms 7 --limit 20
```

### Update Game Data

```bash
# Re-import a game to update its data
../venv/bin/python3 sync_game.py 3328
```

### Browse Your Collection

```bash
# Use collectibles-manager to browse
cd ../collectibles-manager/scripts

# See all games
../venv/bin/python3 search_entities.py --type video_game

# Search for specific games
../venv/bin/python3 search_entities.py --name "zelda" --type video_game

# View franchise hierarchy
../venv/bin/python3 list_hierarchy.py "The Legend of Zelda"
```

## API Rate Limits

MobyGames API limits:
- **Strict enforcement**: 1 request per second
- **No burst allowance**: Must wait full 1 second between requests
- Scripts include 1.1 second rate limiting to ensure compliance
- Heavy usage may trigger temporary blocks - space out bulk imports

## Entity Naming Conventions

**Franchises:**
- Format: Official franchise name
- Examples:
  - "The Legend of Zelda"
  - "Final Fantasy"
  - "Dark Souls"

**Collections/Series:**
- Format: Series name or collection identifier
- Examples:
  - "Mario Kart"
  - "Dark Souls Series"
  - "The Witcher Trilogy"

**Games:**
- Format: Official game title (exact spelling from MobyGames)
- Examples:
  - "Pokémon Sword"
  - "Pokémon Shield"
  - "Pokémon Red Version"
  - "Pokémon Blue Version"
  - "The Legend of Zelda: Breath of the Wild"

**Editions:**
- Format: "{Game Title} - {Edition Type}"
- Examples:
  - "Pokémon Sword + Pokémon Sword Expansion Pass"
  - "The Witcher 3: Wild Hunt - Game of the Year Edition"
  - "Dark Souls: Remastered"

## External ID Format

**Games:**
```json
{
  "mobygames": "137306"
}
```

These IDs are used to prevent duplicate imports and enable updates. Each MobyGames game ID represents a unique game title (e.g., Pokémon Sword has a different ID than Pokémon Shield).

## Platform IDs (Common)

**Nintendo:**
- `10` - Game Boy
- `11` - Game Boy Color
- `12` - Game Boy Advance
- `20` - Nintendo DS
- `44` - Nintendo 3DS
- `203` - Nintendo Switch

**PlayStation:**
- `7` - PlayStation
- `8` - PlayStation 2
- `16` - PlayStation 3
- `81` - PlayStation 4
- `288` - PlayStation 5

**Xbox:**
- `142` - Xbox
- `15` - Xbox 360
- `69` - Xbox One
- `289` - Xbox Series X/S

**Other:**
- `4` - PC
- `3` - iOS
- `7` - Android

## Resources

### scripts/
Python scripts for video game operations:
- `search_api.py` - Search MobyGames API
- `sync_game.py` - Import a single game
- `lib/api_client.py` - MobyGames API client
- `lib/db_client.py` - Database operations

All scripts support `--help` flag for detailed usage.

## Future Enhancements

Potential additions:
- Image scraping from MobyGames website (not available via API)
- Bulk import workflow (respecting rate limits)
- Multiple platform versions per game
- Achievement tracking
- Collection value tracking
- Box condition/grading integration
