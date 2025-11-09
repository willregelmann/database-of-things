# NTSC Video Games Curator Plan

## Collection Goal

Import physical NTSC video game releases from North America across all gaming platforms.

## Scope

- **Items**: Physical game cartridges/discs only (no digital releases)
- **Region**: North America only
- **Platforms**: All consoles (NES, SNES, N64, Genesis, PlayStation, Xbox, etc.)
- **Variants**: Base games only, no special editions or variants
- **Deduplication**: Same game on different platforms = different entities (physical media differs)

## Data Source

**MobyGames API** (https://www.mobygames.com/info/api/)
- Comprehensive video game database with excellent North American coverage
- Provides platform-specific release information
- Includes images, release dates, publishers, developers

## Rate Limiting

MobyGames has aggressive rate limits (~1 request per second, 360/hour for free tier):
- Fetch script will import small batches (10-50 games at a time)
- Built-in sleep delays between requests
- Designed for incremental imports over time

## Import Strategy

### Phase 1: Small Batch Testing
1. Fetch 10-20 games to test pipeline
2. Verify data quality and deduplication
3. Validate image localization

### Phase 2: Platform-by-Platform
Import games by platform to stay organized:
1. Start with classic platforms (NES, SNES, Genesis)
2. Add PlayStation/N64 era
3. Expand to modern consoles

### Phase 3: Ongoing Maintenance
- Re-run fetch script periodically for new releases
- Existing games auto-detected via MobyGames ID

## Data Mapping

### MobyGames → Database Entity

```python
{
  "id": uuid,
  "name": f"{game_title} ({platform_name})",  # e.g., "Super Mario Bros. (NES)"
  "type": "game",
  "year": release_year,
  "country": "US",
  "language": "en",
  "image_url": localized_image_path,
  "thumbnail_url": localized_thumbnail_path,
  "source_url": moby_games_url,
  "external_ids": {
    "moby_games": f"{game_id}-{platform_id}"  # Compound key
  },
  "attributes": {
    "platform": platform_name,
    "platform_id": platform_id,
    "game_id": game_id,
    "publisher": publisher_name,
    "developer": developer_name,
    "genre": [genres],
    "description": game_description
  }
}
```

### Deduplication

- **External ID Format**: `{game_id}-{platform_id}` (e.g., "1234-15" for game 1234 on platform 15)
- **Rationale**: Physical NES cartridge vs SNES cartridge are different collectibles
- **Lookup**: Query `external_ids->>'moby_games'` before inserting

## Technical Notes

### API Endpoints

```
GET /games?limit=10&offset=0&platform=15  # List games for platform
GET /games/{id}                            # Game details
GET /games/{id}/platforms/{platform_id}   # Platform-specific info
GET /platforms                             # List all platforms
```

### Rate Limit Handling

```python
import time

RATE_LIMIT_DELAY = 1.5  # 1.5 seconds between requests (conservative)

for game in games:
    fetch_game_details(game_id)
    time.sleep(RATE_LIMIT_DELAY)
```

### Image Handling

- MobyGames provides cover art via `/games/{id}/platforms/{platform_id}/covers`
- Localize to Supabase storage with thumbnails
- Fallback to external URL if download fails

## Success Criteria

- ✅ Fetch script successfully retrieves game data from MobyGames
- ✅ Rate limiting prevents API errors
- ✅ Deduplication works (no duplicate imports)
- ✅ Images localized to storage with thumbnails
- ✅ Can import incrementally without conflicts
- ✅ Dry run validates complete pipeline
