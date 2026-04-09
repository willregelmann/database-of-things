# NTSC Video Games Curator

Autonomous curator for importing physical NTSC video game releases from MobyGames.

## Overview

- **Source**: MobyGames API
- **Region**: North America (US)
- **Scope**: Physical releases only, all consoles
- **Rate Limits**: ~1 request per 1.5 seconds (360/hour)
- **Import Strategy**: Small batches (10-50 games at a time)

## Multi-Collection Design

**This curator serves multiple platform collections.**

Unlike single-collection curators (Marvel Comics, Power Rangers), this curator is a **reusable import pipeline** that can target different platform collections:

```
NTSC Video Games Curator (import pipeline)
├─> imports to: Game Boy Games collection
├─> imports to: NES Games collection
├─> imports to: SNES Games collection
└─> imports to: PlayStation Games collection
```

**Workflow:**
1. Create a platform collection (e.g., "Game Boy Games")
2. Configure `PLATFORM_ID` and `COLLECTION_ID` in `secrets.env`
3. Run import - games go into that specific collection
4. Repeat for other platforms

This design allows one curator to maintain multiple platform collections without duplication.

## Quick Start

### 1. Create Platform Collection

First, create a collection entity for the platform you want to import:

```sql
INSERT INTO entities (name, type, year, country, language, attributes)
VALUES (
  'Game Boy Games',
  'collection',
  1989,
  'US',
  'en',
  jsonb_build_object(
    'description', 'Physical Game Boy cartridges released in North America',
    'platform', 'Game Boy',
    'platform_id', 10
  )
)
RETURNING id;
```

Note the returned UUID - you'll need it for the next step.

### 2. Configure Curator

Edit `secrets.env` with your collection ID and platform:

```bash
# MobyGames API key
MOBY_GAMES_API_KEY=moby_HeFOMCcpF4PkxwwbxKH6kRcVCyW

# Target collection (from step 1)
COLLECTION_ID=your-collection-uuid-here

# Target platform
PLATFORM_ID=10  # Game Boy
FETCH_LIMIT=10
```

### 3. Run Dry Run (Recommended)

Test the complete pipeline without writing to database:
```bash
cd scripts
python3 import_items.py --dry-run
```

This will:
- Fetch games from MobyGames (respects rate limits)
- Validate image URLs
- Show what would be imported
- Save validation report to `dry_run_results.json`

### 4. Import Games

After dry run succeeds, import to database:
```bash
python3 import_items.py
```

## Configuration

Edit `secrets.env` to customize:

```bash
# Fetch more/fewer games
FETCH_LIMIT=20

# Skip first N games (pagination)
FETCH_OFFSET=100

# Target specific platform (optional)
# Common platform IDs:
#   18 = NES
#   12 = SNES
#   9  = Nintendo 64
#   7  = PlayStation
#   21 = PlayStation 2
PLATFORM_ID=18
```

## MobyGames Platform IDs

Common NTSC platforms:

| ID | Platform |
|----|----------|
| 18 | NES |
| 12 | SNES |
| 16 | Genesis |
| 9  | Nintendo 64 |
| 20 | GameCube |
| 82 | Wii |
| 203 | Nintendo Switch |
| 7  | PlayStation |
| 21 | PlayStation 2 |
| 81 | PlayStation 3 |
| 141 | PlayStation 4 |
| 145 | PlayStation 5 |
| 13 | Xbox |
| 69 | Xbox 360 |
| 142 | Xbox One |
| 144 | Xbox Series |
| 10 | Game Boy |
| 11 | Game Boy Color |
| 14 | Game Boy Advance |
| 44 | Nintendo DS |
| 101 | Nintendo 3DS |
| 46 | PSP |

Full list: https://www.mobygames.com/platform/

## Rate Limiting

MobyGames free tier allows ~360 requests per hour (1 per second).

The fetch script includes built-in delays (1.5 seconds between requests) to stay well under the limit.

**If you hit rate limits:**
- Error message: "Rate limit exceeded. Wait 1 hour and try again."
- Wait 60 minutes before re-running
- Consider reducing `FETCH_LIMIT`

## Incremental Imports

The curator is designed for incremental imports:

1. **First run**: Import 10-20 games
2. **Subsequent runs**: Increase `FETCH_OFFSET` to skip already-imported games
3. **Platform-by-platform**: Use `PLATFORM_ID` to import one platform at a time

Example workflow:
```bash
# Day 1: NES games (first 20)
PLATFORM_ID=18 FETCH_LIMIT=20 FETCH_OFFSET=0 python3 import_items.py

# Day 2: NES games (next 20)
PLATFORM_ID=18 FETCH_LIMIT=20 FETCH_OFFSET=20 python3 import_items.py

# Day 3: SNES games
PLATFORM_ID=12 FETCH_LIMIT=20 FETCH_OFFSET=0 python3 import_items.py
```

## Data Schema

Each game is stored as an entity:

```json
{
  "name": "Super Mario Bros.",
  "type": "video_game",
  "year": 1985,
  "country": "US",
  "language": "en",
  "image_url": "/storage/v1/object/public/images/originals/uuid.jpg",
  "thumbnail_url": "/storage/v1/object/public/images/thumbnails/uuid.webp",
  "source_url": "https://www.mobygames.com/game/1234",
  "external_ids": {
    "moby_games": "1234-18"
  },
  "attributes": {
    "platform": "NES",
    "game_id": 1234,
    "publisher": "Nintendo",
    "developer": "Nintendo R&D4"
  }
}
```

**Key Design Decisions:**
- **Name**: Just the game title (no platform suffix). Platform stored in `attributes->platform`
- **Type**: `video_game` (not `game`)
- **External ID**: Compound key `{game_id}-{platform_id}` for deduplication
- **Attributes**: Platform, publisher, developer (domain-specific metadata)

**Deduplication**: Same game on different platforms = different entities
- "Super Mario Bros." on NES has external_id `1234-18`
- "Super Mario Bros." on Game Boy Advance has external_id `1234-14`
- Both are separate collectibles (different physical media)
- Each lives in its respective platform collection

## Troubleshooting

**No games found**:
- Check that platform ID is valid
- Try removing `PLATFORM_ID` to search all platforms
- Increase `FETCH_LIMIT`

**Rate limit errors**:
- Wait 1 hour
- Reduce `FETCH_LIMIT` to 5-10

**Image localization fails**:
- Images fall back to external MobyGames URLs
- Not a critical error, import continues

**API key invalid**:
- Verify key in secrets.env
- Get new key at: https://www.mobygames.com/info/api/ (when portal is available)

## Architecture

Following curator best practices:

- ✅ **Deduplication**: MobyGames compound ID (`{game_id}-{platform_id}`)
- ✅ **Image localization**: Downloads covers to Supabase storage with thumbnails
- ✅ **Embeddings**: Generates semantic search vectors for all game names
- ✅ **Rate limiting**: Built-in delays to respect API limits
- ✅ **Incremental imports**: Re-running script updates relationships, no duplicates
- ✅ **Dry run support**: Test pipeline before committing to database
- ✅ **Progress tracking**: Clear feedback during fetch and import

## Creating New Platform Collections

To add another platform (e.g., NES):

**1. Create collection:**
```sql
INSERT INTO entities (name, type, year, country, language, attributes)
VALUES (
  'NES Games',
  'collection',
  1985,
  'US',
  'en',
  jsonb_build_object(
    'description', 'Physical NES cartridges released in North America',
    'platform', 'NES',
    'platform_id', 18
  )
)
RETURNING id;
```

**2. Find a logo** and localize it (see Game Boy example in git history)

**3. Update `secrets.env`:**
```bash
COLLECTION_ID=nes-collection-uuid
PLATFORM_ID=18
```

**4. Run import:**
```bash
python3 scripts/import_items.py
```

The same curator serves all your platform collections!

## Future Enhancements

Possible improvements:
- Import box scans (MobyGames has cover art variants)
- Add game series relationships (e.g., all Mario games)
- Import precise release dates (currently year only)
- Platform-specific attributes (cartridge type, region variants, etc.)
- Support for PAL/Japan regions (new curators)
