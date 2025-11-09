# NTSC Video Games Curator

Autonomous curator for importing physical NTSC video game releases from MobyGames.

## Overview

- **Source**: MobyGames API
- **Region**: North America (US)
- **Scope**: Physical releases only, all consoles
- **Rate Limits**: ~1 request per 1.5 seconds (360/hour)
- **Import Strategy**: Small batches (10-50 games at a time)

## Quick Start

### 1. Set API Key

Already configured in `secrets.env`:
```bash
MOBY_GAMES_API_KEY=moby_HeFOMCcpF4PkxwwbxKH6kRcVCyW
```

### 2. Run Dry Run (Recommended)

Test the complete pipeline without writing to database:
```bash
cd scripts
python3 import_items.py --dry-run
```

This will:
- Fetch 10 games from MobyGames (respects rate limits)
- Validate image URLs
- Show what would be imported
- Save validation report to `dry_run_results.json`

### 3. Import Games

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
  "name": "Super Mario Bros. (NES)",
  "type": "game",
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
    "platform_id": 18,
    "game_id": 1234,
    "title": "Super Mario Bros.",
    "genres": ["Platform", "Action"],
    "description": "..."
  }
}
```

**Deduplication**: Same game on different platforms = different entities
- "Super Mario Bros. (NES)" has ID `1234-18`
- "Super Mario Bros. (Game Boy Advance)" has ID `1234-14`
- Both are separate collectibles (different physical media)

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

## Future Enhancements

Possible improvements:
- Fetch publisher/developer (requires additional API calls)
- Import box scans (MobyGames has cover art variants)
- Add game series relationships
- Import release dates (day-level precision)
- Platform-specific attributes (cartridge type, memory cards, etc.)
